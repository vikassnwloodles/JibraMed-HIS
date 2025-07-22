# SPDX-FileCopyrightText: 2019-2022 Chris Zimmerman <chris@teffalump.com>
# SPDX-FileCopyrightText: 2021-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2023 Patryk Rosik <p.rosik@stud.uni-hannover.de>
# SPDX-FileCopyrightText: 2023 Feng Shu <tumashu@163.com>
# SPDX-FileCopyrightText: 2021-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                         HEALTH ORTHANC package                        #
#                     health_orthanc.py: main module                    #
#########################################################################

"""
Core module of the Orthanc DICOM Server integration.

This module provides models for synchronization between an Orthanc DICOM
Server and the GNU Health HMIS. It provides methods to check when the
last synchronization took  place and makes them available to users via
appropriate GUI elements. Additionally,  there are methods to provide
hyperlinks to the corresponding studies and patients for
given Orthanc DICOM servers.
"""

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pyson import Eval, Not, Bool
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.modules.health.core import (get_institution,
                                         compute_age_from_dates,
                                         parse_compute_age)

from beren import Orthanc as RestClient
from requests.auth import HTTPBasicAuth as auth
from datetime import datetime
from urllib.parse import urljoin
from genshi.template import TextTemplate
from pydicom.uid import generate_uid
from requests.exceptions import HTTPError, RequestException

import logging
import pendulum

__all__ = [
    "OrthancWorklistTemplate",
    "OrthancServerConfig",
    "OrthancPatient",
    "OrthancStudy",
    "ImagingTestRequest",
    "ImagingTest",
    "Patient",
    "TestResult",
]

logger = logging.getLogger(__name__)

# XXX: Maybe we should find a better org root string for
# gnuhealth, or let org root string configable.
gnuhealth_org_root = '1.2.836.0.1.3240043.7.198.'


class OrthancWorklistTemplate(ModelSQL, ModelView):
    """Orthanc Worklist Template"""
    __name__ = "gnuhealth.orthanc.worklist.template"
    _rec_name = "name"

    name = fields.Char(
        "Name", required=True,
        help="Worklist template name")

    template = fields.Text(
        "Template", required=True,
        help="Genshi syntax template used to create worklist text, "
        "with dump2dcm command of dcmtk help, worklist text file can "
        "be converted to a .wl file.")

    dump_file_encoding = fields.Char(
        'Encoding',
        help='Encoding used to save worklist text to dump file '
        'by python script, it should work well with (0008,0005) '
        'dicom tag of worklist template, for example: '
        'if (0008,0005) = [ISO_IR 192], encoding should be "utf-8", '
        'if (0008,0005) = [GBK], encoding should be "gbk". ')

    @staticmethod
    def default_dump_file_encoding():
        return 'utf-8'

    comment = fields.Text('Comment')

    @staticmethod
    def default_template():
        template = """\
(0008,0005) SH [ISO_IR 192]
(0008,0201) SH [$TimezoneOffsetFromUTC]
(0008,0050) SH [$AccessionNumber]
(0040,1001) SH [$RequestedProcedureID]
(0020,000d) UI [$StudyInstanceUID]
(0010,0010) PN [$PatientName]
(0010,0020) LO [$PatientID]
(0010,1010) AS [$PatientAge]
(0010,0030) DA [$PatientBirthDate]
(0010,0040) CS [$PatientSex]
(0032,1032) PN [$RequestingPhysician]
(0032,1033) LO [$RequestingService]
(0008,0090) PN [$ReferringPhysicianName]
(0008,0080) LO [$InstitutionName]
(0032,1060) LO [$RequestedProcedureDescription]
(0040,0100) SQ (Sequence with undefined length)
  (fffe,e000) na (Item with undefined length)
    (0008,0060) CS [$Modality]
    (0040,0001) AE [$ScheduledStationAETitle]
    (0040,0002) DA [$ScheduledProcedureStepStartDate]
    (0040,0003) TM [$ScheduledProcedureStepStartTime]
  (fffe,e00d) na (ItemDelimitationItem)
(fffe,e0dd) na (SequenceDelimitationItem)
"""
        return template


class OrthancServerConfig(ModelSQL, ModelView):
    """Orthanc server details"""

    """
    Orthanc server details.

    This class is used to connect to an Orthanc DICOM server. It also
    provides methods to establish synchronicity between the endpoints
    and to check if a connection to the corresponding domain
    can be established.

    :param ModelSQL: Inherit from the Tryton ModelSQL class for SQL
                      database operations.
    :type ModelSQL: class: ``trytond.model.ModelSQL``

    :param ModelView: Inherit from the Tryton ModelView class
                      for user interface operations.
    :type ModelView: class: ``trytond.model.ModelView``

    :var __name__: The unique name ``gnuhealth.orthanc.config`` of the model.
    :vartype __name__: str

    :var _rec_name: The name ``label`` of the field used as name of records.
    :vartype _rec_name: str

    :var label: Label for the server that is displayed to the user. Required.
    :vartype label: class: ``trytond.model.fields.Char``

    :var domain: The full URL for the Orthanc DICOM server. Required.
    :vartype domain: class: ``trytond.model.fields.Char``

    :var user: Username of an authorized user for the Orthanc DICOM
        Server. Required.
    :vartype user: class: ``trytond.model.fields.Char``

    :var password: Password of an authorized user with corresponding name
        for the Orthanc DICOM Server. Required.
    :vartype password: class: ``trytond.model.fields.Char``

    :var last: Index of last change. Read-only.
    :vartype last: class: ``trytond.model.fields.BigInteger``

    :var sync_time: Time of last server syncronization. Read-only.
    :vartype sync_time: class: ``trytond.model.fields.DateTime``

    :var validated: Whether the server details have been successfully checked.
    :vartype validated: class: ``trytond.model.fields.Boolean``

    :var since_sync: Time elapsed since last synchronization (numeric).
    :vartype since_sync: class: ``trytond.model.fields.TimeDelta``

    :var since_sync_readable: Time elapsed since last synchronization
        (human readable).
    :vartype since_sync_readable: class: ``trytond.model.fields.Char``

    :var patients: List of Orthanc patients directly related to the server.
    :vartype patients: class: ``trytond.model.fields.One2Many``

    :var studies: List of Orthanc studies directly related to the server.
    :vartype studies: class: ``trytond.model.fields.One2Many``

    :var link: Hyperlink to the server in the Orthanc explorer.
    :vartype link: class: ``trytond.model.fields.Char``

    :var http_error_messages: A dict of http error and their status codes.
    :vartype http_error_messages: dict
    """

    __name__ = "gnuhealth.orthanc.config"
    _rec_name = "label"

    label = fields.Char(
        "Label", required=True, help="Label for server (eg., remote1)")

    domain = fields.Char(
        "URL", required=True, help="The full URL of the Orthanc server")

    user = fields.Char(
        "Username", required=True, help="Username for Orthanc REST server")

    password = fields.Char(
        "Password", required=True, help="Password for Orthanc REST server")

    last = fields.BigInteger(
        "Last Index", readonly=True, help="Index of last change")

    sync_time = fields.DateTime(
        "Sync Time", readonly=True, help="Time of last server sync")

    validated = fields.Boolean(
        "Validated", help="Whether the server details have been "
        "successfully checked")

    since_sync = fields.Function(
        fields.TimeDelta("Since last sync", help="Time since last sync"),
        "get_since_sync",)

    since_sync_readable = fields.Function(
        fields.Char("Since last sync", help="Time since last sync"),
        "get_since_sync_readable",
    )
    patients = fields.One2Many(
        "gnuhealth.orthanc.patient", "server", "Patients")

    studies = fields.One2Many("gnuhealth.orthanc.study", "server", "Studies")
    link = fields.Function(
        fields.Char(
            "URL",
            help="Link to server in Orthanc Explorer"), "get_link")

    def get_link(self, name):
        pre = "".join([self.domain.rstrip("/"), "/"])
        add = "app/explorer.html"
        return urljoin(pre, add)

    use_stone_viewer = fields.Boolean(
        "Use Stone Viewer",
        help="Use Stone Web Viewer")

    @staticmethod
    def default_use_stone_viewer():
        return False

    use_osimis_viewer = fields.Boolean(
        "Use Osimis Viewer",
        help="Use Osimis Web Viewer")

    @staticmethod
    def default_use_osimis_viewer():
        return False

    @classmethod
    def __setup__(cls):
        """
        Set up the OrthancServerConfig class for database access.

        This method is a class method that initializes various properties
        and constraints of the OrthancServerConfig model. It sets up a SQL
        constraint to ensure that the ``label`` coulmn is unique, and adds
        a custom button to the form view called ``do_sync``. The ``do_sync``
        button triggers a synchronization process between the Orthanc DICOM
        server and the GNU Health HMIS to retrieve and use patient and
        image information from Orthanc.
        """

        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ("label_unique", Unique(t, t.label), "The label must be unique.")
        ]
        cls._buttons.update({"do_sync": {}})

    @classmethod
    @ModelView.button
    def do_sync(cls, servers):
        """
        Start a synchronization.

        :param servers: A list of Orthanc DICOM servers.
        :type servers: list

        :raises UserWarning: Triggered when invalid credentials,
            an invalid domain, a general HTTP error occurs or
            another request error.

        .. note:: This method follows the Tryton Syntax. The
                ``@ModelView.button`` decorates the method
                to check group access and rule.
        .. seealso:: ``button`` from class: ``trytond.model.ModelView``
        """
        try:
            cls.sync(servers)
        except ConnectionRefusedError as exc:
            raise UserWarning(
                "connection_error",
                "Connection not possible. Check the user, password,"
                "URL and port of the server."
            ) from exc
        except HTTPError as err:
            status_code = err.response.status_code
            if status_code in cls.http_error_messages:
                raise UserWarning(
                    "http_error",
                    cls.http_error_messages[status_code]) from None
            raise UserWarning(
                    "unhandled_http", "Unhandled HTTP error") from None
        except RequestException as exc:
            raise UserWarning(
                "request_error", "Unhandled request error occured") from exc
        except Exception as err:
            raise UserWarning(
                "unhandled_error", "Unhandled error occured") from err

    @classmethod
    def sync(cls, servers=None):
        """
        Synchronize patient and study data from Orthanc DICOM servers
        into GNU Health HMIS.

        :param servers: Optional list of ``OrthancServerConfig`` objects,
            which represent orthanc server to synchronize.
            If not provided, all validated servers will be synchronized.
        :type servers: list
        """

        pool = Pool()
        patient = pool.get("gnuhealth.orthanc.patient")
        study = pool.get("gnuhealth.orthanc.study")

        if not servers:
            servers = cls.search([("domain", "!=", None),
                                  ("validated", "=", True)])

        logger.info("Starting sync")
        for server in servers:
            if not server.validated:
                continue
            logger.info("Getting new changes for <{}>".format(server.label))
            orthanc = RestClient(server.domain,
                                 auth=auth(server.user, server.password))
            curr = server.last
            new_patients = set()
            update_patients = set()
            new_studies = set()
            update_studies = set()

            while True:
                try:
                    changes = orthanc.get_changes(since=curr)
                except ConnectionRefusedError:
                    server.validated = False
                    logger.exception(
                        "No connection to the server can be established."
                        "Check connectivity and port."
                    )
                except HTTPError as err:
                    server.validated = False
                    status_code = err.response.status_code
                    if status_code in cls.http_error_messages:
                        error_message = (
                            cls.http_error_messages[status_code] +
                            f" {server. label} not reacheable"
                        )
                        logger.exception(error_message)
                    else:
                        logger.exception(
                            "Unhandled HTTP error for <%s>", server.label)
                except RequestException:
                    server.validated = False
                    logger.exception(
                        "Unhandled request error occured for <%s>",
                        server.label)
                for change in changes["Changes"]:
                    type_ = change["ChangeType"]
                    if type_ == "NewStudy":
                        new_studies.add(change["ID"])
                    elif type_ == "StableStudy":
                        update_studies.add(change["ID"])
                    elif type_ == "NewPatient":
                        new_patients.add(change["ID"])
                    elif type_ == "StablePatient":
                        update_patients.add(change["ID"])
                    else:
                        pass
                curr = changes["Last"]

                if changes["Done"] is True:
                    logger.info("<{}> at newest change".format(server.label))
                    break

            update_patients -= new_patients
            update_studies -= new_studies
            if new_patients:
                patient.create_patients(
                    [orthanc.get_patient(p) for p in new_patients], server
                )
            if update_patients:
                patient.update_patients(
                    [orthanc.get_patient(p) for p in update_patients], server
                )
            if new_studies:
                study.create_studies(
                    [orthanc.get_study(s) for s in new_studies], server
                )
            if update_studies:
                study.update_studies(
                    [orthanc.get_study(s) for s in update_studies], server
                )
            server.last = curr
            server.sync_time = datetime.now()
            logger.info(
                f"\n\nOrthanc server synchronization summary "
                f"from {server.label} :\n"
                f"Patients: New: {len(new_patients)} | "
                f"Updated: {len(update_patients)}\n"
                f"Studies: New: {len(new_studies)} |"
                f"Updated: {len(update_studies)}\n"
                 )

        cls.save(servers)

    @staticmethod
    def quick_check(domain, user, password):
        """
        Check if the server details are correct.

        :param domain: The domain name or IP address of the Orthanc
                       DICOM server.
        :type domain: str

        :param user: The username for authentication.
        :type user: str

        :param password: The password for authentication.
        :type password: str

        :return: ``True`` if the server details are valid,
                 ``False`` otherwise.
        :rtype: bool
        """

        try:
            orthanc = RestClient(domain, auth=auth(user, password))
            orthanc.get_changes(last=True)
        except ConnectionError:
            logger.exception(
                "No connection to the server can be established."
                "Check connectivity and port."
            )
            return False
        except HTTPError as err:
            status_code = err.response.status_code
            if status_code in OrthancServerConfig.http_error_messages:
                error_message = (
                    OrthancServerConfig.http_error_messages[status_code] +
                    f" {domain} not reacheable"
                )
                logger.exception(error_message)
            else:
                logger.exception("Unhandled HTTP error for <%s>", domain)
            return False
        except RequestException:
            logger.exception(
                "Unhandled request error for <%s> occurred", domain)
            return False
        return True

    @fields.depends("domain", "user", "password")
    def on_change_with_validated(self):
        """
        Update the ``validated`` field based on the current server details.

        :return: A boolean value indicating whether the update was
                 successful or not.
        :rtype: bool

        .. note:: This method follows the Tryton Syntax. The
                  ``@fields.depends`` decorates the method to indicate
                    that this field depends on other fields. In addition,
                    ``on_change_with_`` is appended before the field name
                    to indicate that the field should change depending on
                    the parameters after ``@fields.depends``.

        .. seealso:: React to user input and Add computed fields in Tryton
                     documentation.
        """

        return self.quick_check(self.domain, self.user, self.password)

    def get_since_sync(self, name):
        """
        Returns the time duration since the last synchronization.

        :param name: Label of the server for which sinc time is to be obtained.
        :type name: string

        :return: The time duration since the last synchronization.
        :rtype: class: ``trytond.model.fields.TimeDelta``
        """

        return datetime.now() - self.sync_time

    def get_since_sync_readable(self, name):
        """
        Returns a human-readable string representing the time duration
        since last synchronization.

        :param name: Label of the server for which sinc time is to be obtained.
        :type name: string

        :return: A string representing the time duration since the last
            synchronization in a human-readable format.
        :rtype: str
        """

        try:
            d = pendulum.now() - pendulum.instance(self.sync_time)
            return d.in_words(Transaction().language)
        except ValueError:
            logger.exception(f"No locale found for {Transaction().language}")
            return d.in_words('en')
        except TypeError:
            return f"No correct instance of {self.sync_time}!"


class OrthancPatient(ModelSQL, ModelView):
    """Orthanc patient information"""
    """
    Defines an Orthanc Patient.

    This class defines the ``OrthancPatient``. It provides methods to update
    existing patients or add new patients from the Orthanc DICOM server.
    Additionally, it allows to extract DICOM tags and automatically generates
    hyperlinks to the corresponding patients.

    :param ModelSQL: Inherit from the Tryton ModelSQL class for SQL
                     database operations.
    :type ModelSQL: class: ``trytond.model.ModelSQL``

    :param ModelView: Inherit from the Tryton ModelView class for user
                      interface operations.
    :type ModelView: class: ``trytond.model.ModelView``

    :var __name__: The unique name ``gnuhealth.orthanc.patient`` of the model.
    :vartype __name__: str

    :var patient: Local linked patient from Orthanc into GNU Health HMIS.
    :vartype patient: class: ``trytond.model.field.Many2One``

    :var name: Name of the patient. Read-only.
    :vartype name: class: ``trytond.model.field.Char``

    :var bd: Birth date of the patient. Read-only.
    :vartype bd: class: ``trytond.model.field.Date``

    :var ident: Unique ID for a patient based on the Patient ID DICOM Tag.
                Read-only.
    :vartype ident: class: ``trytond.model.field.Char``

    :var uuid: SHA-1 Hash of ``ident``. Read-only and Required.
    :vartype uuid: class: ``trytond.model.field.Char``

    :var studies: List of Orthanc studies directly related to the patient.
                  Read-only.
    :vartype studies: class: ``trytond.model.field.One2Many``

    :var server:  A field to specify the server. Required.
    :vartype server: class: ``trytond.model.field.Many2One``

    :var link: Link to the patient in the Orthanc Explorer.
    :vartype link: class: ``trytond.model.field.Char``
    """

    __name__ = "gnuhealth.orthanc.patient"

    patient = fields.Many2One(
        "gnuhealth.patient", "Patient", help="Local linked patient"
    )
    name = fields.Char("PatientName", readonly=True)
    bd = fields.Date("Birthdate", readonly=True)
    ident = fields.Char("PatientID", readonly=True)
    uuid = fields.Char("PatientUUID", readonly=True, required=True)
    studies = fields.One2Many(
        "gnuhealth.orthanc.study", "patient", "Studies", readonly=True
    )
    server = fields.Many2One(
        "gnuhealth.orthanc.config", "Server", readonly=True)
    link = fields.Function(
        fields.Char(
            "URL", help="Link to patient in Orthanc Explorer"), "get_link"
            )

    def get_link(self, name):
        """
        Return a link to the Orthanc patient with the specified uuid in
        the Orthanc explorer.

        :param name: Label of the patient to get the link for.
        :type name: str

        :return: URL to the Orthanc patient in the Orthanc Explorer.
        :rtype: str
        """

        pre = "".join([self.server.domain.rstrip("/"), "/"])
        add = "app/explorer.html#patient?uuid={}".format(self.uuid)
        return urljoin(pre, add)

    @classmethod
    def __setup__(cls):
        """
        Set up the ``OrthancPatient`` class for database access.

        This method is a class method that initializes various properties
        and constraints of the ``OrthancPatient`` model. It sets up a SQL
        constraint to ensure that the ``server`` and  ``uuid`` column
        are unique.
        """

        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            (
                "uuid_unique",
                Unique(t, t.server, t.uuid),
                "UUID must be unique for a given server",
            )
        ]

    @staticmethod
    def get_info_from_dicom(patients):
        """
        Extract patient information from DICOM data for writing to database.

        :param patients: List of DICOM data for patients.
        :type patients: list

        :return: List of dictionaries with patient information.
        :rtype: list
        """

        data = []
        for patient in patients:
            try:
                bd = datetime.strptime(
                    patient["MainDicomTags"]["PatientBirthDate"], "%Y%m%d"
                ).date()

            except Exception:
                logger.exception(
                    "Invalid date format. Please provide the date in "
                    "the format %Y%m%d"
                )
                bd = None
            data.append(
                {
                    "name": patient.get("MainDicomTags").get("PatientName"),
                    "bd": bd,
                    "ident": patient.get("MainDicomTags").get("PatientID"),
                    "uuid": patient.get("ID"),
                }
            )
        return data

    @classmethod
    def update_patients(cls, patients, server):
        """
        Update patients with new information from DICOM files.

        :param patients: A list of patient data in DICOM format.
        :type patients: list

        :param server: The server to update the patients on.
        :type server: str
        """

        entries = cls.get_info_from_dicom(patients)
        updates = []
        for entry in entries:
            try:
                patient = cls.search(
                    [("uuid", "=", entry["uuid"]),
                     ("server", "=", server)], limit=1
                )[0]
                patient.name = entry["name"]
                patient.bd = entry["bd"]
                patient.ident = entry["ident"]
                # don't update unless no patient attached
                if not patient.patient:
                    try:
                        g_patient = Patient.search(
                            [("puid", "=", entry["ident"])], limit=1
                        )[0]
                        patient.patient = g_patient
                        logger.info(
                            "New Matching PUID found for {}".
                            format(entry["ident"])
                        )
                    except IndexError:
                        logger.warning(
                            "No patient from GNU Health HMIS attached")
                updates.append(patient)
                logger.info("Updating patient {}".format(entry["uuid"]))
            except IndexError:
                continue
                logger.warning("Unable to update patient {}".
                               format(entry["uuid"]))
        cls.save(updates)

    @classmethod
    def create_patients(cls, patients, server):
        """
        Create patients with information from DICOM files.

        :param patients: A list of patient data in DICOM format.
        :type patients: list

        :param server: The server to update the patients on.
        :type server: str
        """

        pool = Pool()
        Patient = pool.get("gnuhealth.patient")

        entries = cls.get_info_from_dicom(patients)
        for entry in entries:
            try:
                g_patient = Patient.search(
                    [("puid", "=", entry["ident"])], limit=1)[0]
                logger.info("Matching PUID found for {}".format(entry["uuid"]))
            except IndexError:
                g_patient = None
            entry["server"] = server
            entry["patient"] = g_patient
        cls.create(entries)


class OrthancStudy(ModelSQL, ModelView):
    """
    Defines an Orthanc Study.

    This class defines the ``OrthancStudy``. It provides methods to update
    existing studies or add new studies to the Orthanc DICOM server.
    Additionally, it allows to extract DICOM tags and automatically generates
    hyperlinks to the corresponding studies.

    :param ModelSQL: Inherit from the Tryton ModelSQL class for SQL
                     database operations.
    :type ModelSQL: class: ``trytond.model.ModelSQL``

    :param ModelView: Inherit from the Tryton ModelView class for user
                      interface operations.
    :type ModelView: class: ``trytond.model.ModelView``

    :var __name__: The unique name `gnuhealth.orthanc.study` of the model.
    :vartype __name__: str

    :var patient: Local patient of Orthanc conncted to a study. Read-only.
    :vartype patient: class: ``trytond.model.fields.Many2One``

    :var uuid: SHA-1 Hash of the PatientID tag (0010,0020) and their
               StudyInstanceUID tag
        (0020,000d). Read-only and Required.
    :vartype uuid: class: ``trytond.model.fields.Char``

    :var description: Description of the study conducted. Read-only.
    :vartype description: class: ``trytond.model.fields.Char``

    :var date: Date on which the study was conducted. Read-only.
    :vartype date: class: ``trytond.model.fields.Date``

    :var ident: ID of a study based on the Study ID DICOM Tag. Read-only.
    :vartype ident: class: ``trytond.model.fields.Char``

    :var institution: Institution at which the study was conducted. Read-only.
    :vartype institution: class: ``trytond.model.fields.Char``

    :var ref_phys: The referring physician. Read-only.
    :vartype ref_phys: class: ``trytond.model.fields.Char``

    :var req_phys: The requesting physician. Read-only.
    :vartype req_phys: class: ``trytond.model.fields.Char``

    :var server: Server on which the study is located. Read-only.
    :vartype server: class: ``trytond.model.fields.Many2One``

    :var link: Link to study in Orthanc Explorer.
    :vartype link: class: ``trytond.model.fields.Char``

    :var imaging_test: Corresponding request from GNU Health HMIS.
    :vartype imaging_test: class: ``trytond.model.fields.Many2One``
    """

    __name__ = "gnuhealth.orthanc.study"

    patient = fields.Many2One(
        "gnuhealth.orthanc.patient", "Patient", readonly=True)

    uuid = fields.Char("UUID", readonly=True, required=True)
    description = fields.Char("Description", readonly=True)
    date = fields.Date("Date", readonly=True)
    ident = fields.Char("ID", readonly=True)
    instance_uid = fields.Char("InstanceUID", readonly=True)
    requested_procedure_id = fields.Char(
        "RequestedProcedureID", readonly=True
    )
    merge_id = fields.Char(
        "Merge ID", readonly=True,
        help="Test result merge id, with it help, "
        "gnuhealth test result and orthanc study can be merged."
    )
    institution = fields.Char(
        "Institution", readonly=True,
        help="Imaging center where study was undertaken"
    )
    ref_phys = fields.Char("Referring Physician", readonly=True)
    req_phys = fields.Char("Requesting Physician", readonly=True)
    server = fields.Many2One(
        "gnuhealth.orthanc.config", "Server", readonly=True)

    link = fields.Function(
        fields.Char(
            "URL", help="Link to study in Orthanc Explorer"), "get_link")

    imaging_test = fields.Many2One("gnuhealth.imaging.test.result", "Study")

    def get_link(self, name):
        """
        Return a link to the Orthanc study with the specified uuid in the
        Orthanc explorer.

        :param name: Label of the study to get the link for.
        :type name: str

        :return: URL to the Orthanc study in the Orthanc Explorer.
        :rtype: str
        """

        pre = "".join([self.server.domain.rstrip("/"), "/"])
        if self.server.use_stone_viewer:
            add = "stone-webviewer/index.html?study={}".format(
                self.instance_uid)
        elif self.server.use_osimis_viewer:
            add = "osimis-viewer/app/index.html?study={}".format(self.uuid)
        else:
            add = "app/explorer.html#study?uuid={}".format(self.uuid)
        return urljoin(pre, add)

    @classmethod
    def __setup__(cls):
        """
        Set up the ``OrthancStudy`` class for database access.

        This method is a class method that initializes various
        properties and constraints of the ``OrthancStudy`` model.
        It sets up a SQL constraint to ensure that the ``server`` and
        ``uuid`` columns are unique.
        """

        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            (
                "uuid_unique",
                Unique(t, t.server, t.uuid),
                "UUID must be unique for a given server",
            )
        ]

    def get_rec_name(self, name):
        """
        Return name of actual study.

        :param name: The name of the record.
        :type name: str

        :return: A string representing the display name of the record.
        :rtype: str

        .. note:: This method follows the Tryton Syntax.
            It is the getter function for the field ``rec_name``.
        .. seealso:: classmethod: ``ModelStorage.get_rec_name` from
            class: ``trytond.model.ModelStorage``
        """

        return ": ".join((self.ident or self.uuid, self.description or ""))

    @classmethod
    def get_info_from_dicom(cls, studies, server):
        """
        Extract study  information from DICOM data for writing to database.

        :param studies: List of DICOM data for studies.
        :type studies: list

        :return: List of dictionaries with study information.
        :rtype: list
        """

        data = []

        for study in studies:
            try:
                date = datetime.strptime(
                    study["MainDicomTags"]["StudyDate"], "%Y%m%d"
                ).date()
            except Exception:
                logger.exception(
                    "Invalid date format. Please provide the date in "
                    "the format %Y%m%d"
                )
                date = None
            try:
                description = \
                    study["MainDicomTags"]["RequestedProcedureDescription"]
            except KeyError:
                logger.warning("No description provided")
                description = None

            entry = {
                "parent_patient": study["ParentPatient"],
                "uuid": study["ID"],
                "description": description,
                "date": date,
                "ident": study.get("MainDicomTags").get("StudyID"),
                "instance_uid": study.get("MainDicomTags").get(
                    "StudyInstanceUID"),
                "requested_procedure_id": study.get("MainDicomTags").get(
                    "RequestedProcedureID"),
                "institution": study.get("MainDicomTags").get(
                    "InstitutionName"),
                "ref_phys": study.get("MainDicomTags").get(
                    "ReferringPhysicianName"
                ),
                "req_phys": study.get(
                    "MainDicomTags").get("RequestingPhysician")
            }

            entry['merge_id'] = cls.get_merge_id(entry, server)

            data.append(entry)

        return data

    @classmethod
    def get_merge_id(cls, entry, server):
        prefix = gnuhealth_org_root

        # In most situations, we use 'StudyInstanceUID' to store merge
        # id.
        if (entry['instance_uid'] or '').startswith(prefix):
            return entry['instance_uid']

        # XXX: for imaging workstation's bugs, sometimes, we use other
        # study tags instead of 'StudyInstanceUID' to store merge id.
        for (k, v) in entry.items():
            if isinstance(v, str) and v.startswith(prefix):
                return v

        # XXX: for imaging workstation's bugs, sometimes, we use
        # 'PatientID' tag to store merge id.
        Patient = Pool().get("gnuhealth.orthanc.patient")
        patient = Patient.search(
            [("uuid", "=", entry["parent_patient"]),
             ("server", "=", server)],
            limit=1)[0]
        if patient:
            if patient.ident:
                if patient.ident.startswith(prefix):
                    return patient.ident

    @classmethod
    def update_studies(cls, studies, server):
        """
        Update studies  with new information from DICOM files.

        :param studies: A list of studies data in DICOM format.
        :type studies: list

        :param server: The server to update the studies on.
        :type server: str
        """

        entries = cls.get_info_from_dicom(studies, server)
        updates = []
        for entry in entries:
            try:
                study = cls.search(
                    [("uuid", "=", entry["uuid"]),
                        ("server", "=", server)], limit=1
                )[0]

                result = cls.find_test_result(entry)

                study.description = entry["description"]
                study.date = entry["date"]
                study.ident = entry["ident"]
                study.instance_uid = entry["instance_uid"]
                study.merge_id = entry["merge_id"]
                study.institution = entry["institution"]
                study.ref_phys = entry["ref_phys"]
                study.req_phys = entry["req_phys"]
                if result:
                    study.imaging_test = result.id
                updates.append(study)
                logger.info("Updating study {}".format(entry["uuid"]))
            except IndexError:
                continue
                logger.warning(
                    "Unable to update study {}".format(entry["uuid"]))
        cls.save(updates)

    @classmethod
    def find_test_result(cls, entry):
        if entry and entry["merge_id"] and len(entry["merge_id"]) > 0:
            Result = Pool().get('gnuhealth.imaging.test.result')
            result = Result.search(
                [("merge_id", "=", entry["merge_id"])],
                limit=1)
            return (result and result[0])

    @classmethod
    def create_studies(cls, studies, server):
        """
        Create studies with information from DICOM files.

        :param studies: A list of studies data in DICOM format.
        :type studies: list

        :param server: The server to update the patients on.
        :type server: str
        """

        pool = Pool()
        Patient = pool.get("gnuhealth.orthanc.patient")

        entries = cls.get_info_from_dicom(studies, server)
        for entry in entries:
            try:
                patient = Patient.search(
                    [("uuid", "=",
                      entry["parent_patient"]), ("server", "=", server)],
                    limit=1,
                )[0]
            except IndexError:
                patient = None
                logger.warning(
                    "No parent patient found for study {}".format(entry["ID"])
                )
            entry.pop("parent_patient")  # remove non-model entry
            entry["server"] = server
            entry["patient"] = patient
            result = cls.find_test_result(entry)
            if result:
                entry["imaging_test"] = result.id

        cls.create(entries)


class ImagingTestRequest(metaclass=PoolMeta):
    __name__ = 'gnuhealth.imaging.test.request'

    computed_age = fields.Function(fields.Char(
        'Age',
        help="Computed patient age at image request."),
        'patient_age_at_imaging_request')

    def patient_age_at_imaging_request(self, name):
        if (self.patient.name.dob and self.date):
            return compute_age_from_dates(
                self.patient.name.dob, None, None, None, 'age',
                self.date.date())

    merge_id = fields.Char("Merge ID")

    @staticmethod
    def default_merge_id():
        # Use DICOM UID format, for most situation, merge id is used
        # as StudyInstanceUID.
        return generate_uid(gnuhealth_org_root)

    show_worklist_text = fields.Boolean('Worklist')

    @staticmethod
    def default_show_worklist_text():
        return False

    worklist_text = fields.Function(
        fields.Text("Worklist text",
                    states={'invisible': Not(
                        Bool(Eval('show_worklist_text')))}),
        'get_worklist_text')

    def get_worklist_text(self, name):
        template = self.get_worklist_template()
        if template:
            data = self.get_worklist_template_data()
            tmpl = TextTemplate(template)
            text = str(tmpl.generate(**data))
            return text
        else:
            return ''

    def get_worklist_template(self):
        template = (self.requested_test.worklist_template and
                    self.requested_test.worklist_template.template)
        return template

    def get_worklist_template_data(self):
        data = {
            # We can not use 'self' as key name, so use 'my'
            # instead.
            'my':                     self,
            'MergeID':                self.merge_id or '',
            'AccessionNumber':        self.getDicomAccessionNumber(),
            'RequestedProcedureID':   self.getDicomRequestedProcedureID(),
            'StudyInstanceUID':       self.getDicomStudyInstanceUID(),
            'PatientName':            self.getDicomPatientName(),
            'PatientID':              self.getDicomPatientID(),
            'PatientAge':             self.getDicomPatientAge(),
            'PatientBirthDate':       self.getDicomPatientBirthDate(),
            'PatientSex':             self.getDicomPatientSex(),
            'RequestingPhysician':    self.getDicomRequestingPhysician(),
            'RequestingService':      self.getDicomRequestingService(),
            'InstitutionName':        self.getDicomInstitutionName(),
            'Modality':               self.getDicomModality(),
            'ReferringPhysicianName':
            self.getDicomReferringPhysicianName(),
            'RequestedProcedureDescription':
            self.getDicomRequestedProcedureDescription(),
            'ScheduledStationAETitle':
            self.getDicomScheduledStationAETitle(),
            'ScheduledProcedureStepStartDate':
            self.getDicomScheduledProcedureStepStartDate(),
            'ScheduledProcedureStepStartTime':
            self.getDicomScheduledProcedureStepStartTime(),
            'TimezoneOffsetFromUTC':
            self.getDicomTimezoneOffsetFromUTC(),
        }
        return data

    def getDicomAccessionNumber(self):
        return self.request or ''

    def getDicomRequestedProcedureID(self):
        return self.request_line or ''

    def getDicomStudyInstanceUID(self):
        return self.merge_id or ''

    def getDicomPatientName(self):
        name = (self.format_dicom_person_name(self.patient.name.id)
                or (self.patient and self.patient.rec_name) or '')
        return name

    def format_dicom_person_name(self, person_id):
        Pname = Pool().get('gnuhealth.person_name')

        try:
            officialname = Pname.search(
                [("party", "=", person_id), ("use", "=", 'official')])[0]
        except BaseException:
            officialname = None

        if officialname:
            family = officialname.family or ''
            given = officialname.given or ''
            # gnuhealth.person_name do not support middle name.
            middle = ''
            prefix = officialname.prefix or ''
            suffix = officialname.suffix or ''
            name = "^".join([
                family, given, middle, prefix, suffix]).rstrip('^')
            return name

    def getDicomPatientID(self):
        return self.patient and self.patient.puid or ''

    def getDicomPatientBirthDate(self):
        dob = self.patient and self.patient.name.dob
        if dob:
            return dob.strftime('%Y%m%d')

    def getDicomPatientAge(self):
        age_str = self.computed_age
        if age_str:
            year, month, day = parse_compute_age(age_str)

            # Handle y, m, d = None
            year = year or '-1'
            month = month or '-1'
            day = day or '-1'

            if year == 0 and month == 0 and day > 0:
                return f'{day:03}D'
            elif year == 0 and month > 0:
                return f'{month:03}M'
            elif year > 0:
                return f'{year:03}Y'
            else:
                return ''

    def getDicomPatientSex(self):
        sex = self.patient and self.patient.gender
        if sex == 'f':
            return 'F'
        elif sex == 'm':
            return 'M'
        else:
            return "O"

    def getDicomRequestingPhysician(self):
        """
        Returns the health professional who requests  the test
        """
        name = (self.format_dicom_person_name(self.doctor.name.id)
                or (self.doctor and self.doctor.rec_name) or '')
        return name

    def getDicomRequestingService(self):
        """
        Returns the specialty of the physician associated to the test
        as the Service
        """
        name = ''
        if (self.doctor.main_specialty):
            name = self.doctor.main_specialty.rec_name
        return name

    def getDicomReferringPhysicianName(self):
        """
        Returns the health professional who sent / derived the patient
        to this unit
        """

        name = (self.format_dicom_person_name(self.doctor.name.id)
                or (self.doctor and self.doctor.rec_name) or '')
        return name

    def getDicomInstitutionName(self):
        # Return the name (string) of the institution
        institution_id = get_institution()
        if institution_id:
            institution = \
                Pool().get('gnuhealth.institution')(institution_id)
            return institution.rec_name
        else:
            return ''

    def getDicomRequestedProcedureDescription(self):
        test = self.requested_test and self.requested_test.rec_name or ''
        return test

    def getDicomScheduledStationAETitle(self):
        aetitle = self.requested_test.aetitle or ''
        return aetitle

    def getDicomScheduledProcedureStepStartDate(self):
        # This is UTC datetime, so we need set dicom tag (0008,0201)
        # 'Timezone Offset From UTC' to '+0000'.
        date = self.date.strftime('%Y%m%d')
        return date

    def getDicomScheduledProcedureStepStartTime(self):
        # This is UTC datetime, so we need set dicom tag (0008,0201)
        # 'Timezone Offset From UTC' to '+0000'.
        time = self.date.strftime('%H%M%S')
        return time

    def getDicomTimezoneOffsetFromUTC(self):
        # Datetimes get from gnuhealth are UTC datetimes, so we need
        # set dicom tag (0008,0201) 'Timezone Offset From UTC' to
        # '+0000'.
        return '+0000'

    def getDicomModality(self):
        test_type = (self.requested_test.test_type and
                     self.requested_test.test_type.code or '')
        return test_type


class ImagingTest(metaclass=PoolMeta):
    __name__ = 'gnuhealth.imaging.test'

    aetitle = fields.Char(
        "AETitle",
        help="AETitle string, used as (0040,0001) "
        "ScheduledStationAETitle tag in worklist template."
    )
    worklist_template = fields.Many2One(
        "gnuhealth.orthanc.worklist.template", "Worklist template"
    )


class TestResult(metaclass=PoolMeta):
    __name__ = "gnuhealth.imaging.test.result"

    """
    Adds Orthanc imaging studies to imaging test result.

    :param ModelSQL: Inherit from the Tryton ModelSQL class for SQL
                     database operations.
    :type ModelSQL: class: ``trytond.model.ModelSQL``

    :param ModelView: Inherit from the Tryton ModelView class for user
                      interface operations.
    :type ModelView: class: ``trytond.model.ModelView``

    :var __name__: The unique name ``gnuhealth.imaging.test.result``
                   of the model.
    :vartype __name__: str
    """

    studies = fields.One2Many(
        "gnuhealth.orthanc.study", "imaging_test", "Orthanc studies",
        readonly=True
    )

    merge_id = fields.Char("Merge ID")

    @classmethod
    def create(cls, vlist):
        Request = Pool().get('gnuhealth.imaging.test.request')
        vlist = [x.copy() for x in vlist]

        for values in vlist:
            request = Request.search(
                [("id", "=", values['request'])], limit=1)[0]

            if request:
                values['merge_id'] = request.merge_id or ''

            studies = cls.find_orthanc_studies(request)

            if studies:
                values['studies'] = [('add', [x.id for x in studies])]

        return super(TestResult, cls).create(vlist)

    @classmethod
    def find_orthanc_studies(cls, request):
        if request and len(request.merge_id) > 0:
            Study = Pool().get('gnuhealth.orthanc.study')
            studies = Study.search(
                [("merge_id", "=", request.merge_id)])
            return studies


class Patient(metaclass=PoolMeta):
    __name__ = "gnuhealth.patient"

    """
    Adds Orthanc patients to the main patient data.

    :param ModelSQL: Inherit from the Tryton ModelSQL class for SQL
                     database operations.
    :type ModelSQL: class: ``trytond.model.ModelSQL``

    :param ModelView: Inherit from the Tryton ModelView class for user
                      interface operations.
    :type ModelView: class: ``trytond.model.ModelView``

    :var __name__: The unique name ``gnuhealth.patient`` of the model.
    :vartype __name__: str
    """

    orthanc_patients = fields.One2Many(
        "gnuhealth.orthanc.patient", "patient", "Orthanc patients"
    )
