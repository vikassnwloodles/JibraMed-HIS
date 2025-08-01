# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                    HEALTH CRYPTO LAB package                          #
#                health_crypto_lab.py: main module                      #
#########################################################################
from datetime import datetime
from trytond.model import ModelView, fields
from trytond.rpc import RPC
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Not, Bool, Equal
import hashlib
import json
from uuid import uuid4
from trytond.modules.health.core import get_health_professional

__all__ = ['LabTest']


class LabTest(metaclass=PoolMeta):
    __name__ = 'gnuhealth.lab'

    STATES = {'readonly': Eval('state') == 'validated'}

    serializer = fields.Text('Doc String', readonly=True)

    document_digest = fields.Char(
        'Digest', readonly=True,
        help="Original Document Digest")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('validated', 'Validated'),
        ], 'State', readonly=True, sort=False)

    digest_status = fields.Function(
        fields.Boolean(
            'Altered',
            help="This field will be set whenever parts of"
            " the main original document has been changed."
            " Please note that the verification is done only on selected"
            " fields."),
        'check_digest')

    serializer_current = fields.Function(
        fields.Text(
            'Current Doc',
            states={
                'invisible': Not(Bool(Eval('digest_status'))),
                }),
        'check_digest')

    digest_current = fields.Function(
        fields.Char(
            'Current Hash',
            states={
                'invisible': Not(Bool(Eval('digest_status'))),
                }),
        'check_digest')

    digital_signature = fields.Text('Digital Signature', readonly=True)

    done_by = fields.Many2One(
        'gnuhealth.healthprofessional',
        'Done by', readonly=True, help='Professional who processes this'
        ' lab test',
        states=STATES)

    done_date = fields.DateTime(
        'Finished on', readonly=True,
        states=STATES)

    validated_by = fields.Many2One(
        'gnuhealth.healthprofessional',
        'Validated by', readonly=True, help='Professional who validates this'
        ' lab test',
        states=STATES)

    validation_date = fields.DateTime(
        'Validated on', readonly=True,
        states=STATES)

    historize = fields.Boolean(
        "Historize",
        states=STATES,
        depends=['pathology'],
        help='If this flag is set'
        ' the a new health condition will be added'
        ' to the patient history.'
        ' Unset it if this lab test is in the context'
        ' of a pre-existing condition of the patient.'
        ' The condition will be created when the lab test'
        ' is confirmed and validated')

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_historize():
        return False

    @fields.depends('pathology')
    def on_change_with_historize(self):
        if (self.pathology):
            return True

    @classmethod
    def __setup__(cls):
        super(LabTest, cls).__setup__()
        cls._buttons.update({
            'generate_document': {
                'invisible': Not(Equal(Eval('state'), 'draft')),
                },
            'set_to_draft': {
                'invisible': Not(Equal(Eval('state'), 'done')),
                },
            'sign_document': {
                'invisible': Not(Equal(Eval('state'), 'done')),
                },
            })
        ''' Allow calling the set_signature method via RPC '''
        cls.__rpc__.update({
                'set_signature': RPC(readonly=False),
                })

    @classmethod
    @ModelView.button
    def generate_document(cls, documents):
        # Set the document to "Done"
        # and write the name of the signing health professional

        hp = get_health_professional()

        cls.write(documents, {
            'done_by': hp,
            'done_date': datetime.now(),
            'state': 'done', })

    @classmethod
    @ModelView.button
    def set_to_draft(cls, documents):
        cls.write(documents, {
            'state': 'draft', })

    @classmethod
    @ModelView.button
    def sign_document(cls, documents):
        document = documents[0]

        # Validate / generate digest for the document
        # and write the name of the signing health professional
        hp = get_health_professional()

        serial_doc = cls.get_serial(document)

        cls.write(documents, {
            'serializer': serial_doc,
            'document_digest': HealthCrypto().gen_hash(serial_doc),
            'validated_by': hp,
            'validation_date': datetime.now(),
            'state': 'validated', })

        # Create lab PoL if the person has a federation account.
        if (document.patient and document.patient.name.federation_account):
            cls.create_lab_pol(document)

        # Create Health condition to the patient
        # if there is a confirmed pathology associated and
        # validated to the lab test result
        # The flag historize must also be set
        if (document.pathology and document.historize):
            cls.create_health_condition(document)

    @classmethod
    def get_serial(cls, document):

        analyte_line = []

        for line in document.critearea:
            line_elements = [
                line.name or '',
                line.result or '',
                line.units and line.units.name or '',
                line.result_text or '',
                line.remarks or '']

            analyte_line.append(line_elements)

        data_to_serialize = {
            'Lab_test': str(document.name) or '',
            'Test': str(document.test.rec_name) or '',
            'HP': document.requestor and str(document.requestor.rec_name) or '',
            'Source_type': str(document.source_type),
            'Patient': document.patient and str(document.patient.rec_name) or '',
            'Other_source': str(document.other_source) or '',
            'Patient_ID': document.patient and str(document.patient.name.ref) or '',
            'Analyte_line': str(analyte_line),
             }

        serialized_doc = str(HealthCrypto().serialize(data_to_serialize))

        return serialized_doc

    @classmethod
    def set_signature(cls, data, signature):
        """
        Set the clearsigned signature
        """

        doc_id = data['id']

        cls.write([cls(doc_id)], {
            'digital_signature': signature,
            })

    def check_digest(self, name):
        result = ''
        serial_doc = self.get_serial(self)
        if (name == 'digest_status' and self.document_digest):
            if (HealthCrypto().gen_hash(serial_doc) == self.document_digest):
                result = False
            else:
                ''' Return true if the document has been altered'''
                result = True
        if (name == 'digest_current'):
            result = HealthCrypto().gen_hash(serial_doc)

        if (name == 'serializer_current'):
            result = serial_doc

        return result

    # Hide the group holding validation information when state is
    # not validated

    @classmethod
    def view_attributes(cls):
        return [('//group[@id="document_digest"]', 'states', {
                'invisible': Not(Eval('state') == 'validated'),
                })]

    @classmethod
    def create_health_condition(cls, lab_info):
        """ Create the health condition when specified and
            validated in the lab test
        """
        HealthCondition = Pool().get('gnuhealth.patient.disease')
        health_condition = []

        vals = {
            'name': lab_info.patient.id,
            'pathology': lab_info.pathology,
            'diagnosed_date': lab_info.date_analysis.date(),
            'lab_confirmed': True,
            'lab_test': lab_info.id,
            'extra_info': lab_info.diagnosis,
            'healthprof': lab_info.requestor
            }

        health_condition.append(vals)
        HealthCondition.create(health_condition)

    @classmethod
    def create_lab_pol(cls, lab_info):
        """ Adds an entry in the person Page of Life
            related to this person lab
        """
        if lab_info.is_patient():
            Pol = Pool().get('gnuhealth.pol')
            pol = []
            
            test_lines = ""
            for line in lab_info.critearea:
                test_lines = test_lines + line.rec_name + "\n"

            vals = {
                'page': str(uuid4()),
                'person': lab_info.patient.name.id,
                'page_date': lab_info.date_analysis,
                'federation_account': 
                    lab_info.patient.name.federation_account,
                'page_type': 'medical',
                'medical_context': 'lab',
                'relevance': 'important',
                'info': lab_info.analytes_summary,
                'author': lab_info.requestor and
                    lab_info.requestor.rec_name
            }

            pol.append(vals)
            Pol.create(pol)


class HealthCrypto:
    """ GNU Health Cryptographic functions
    """
    def serialize(self, data_to_serialize):
        """ Format to JSON """

        json_output = \
            json.dumps(data_to_serialize, ensure_ascii=False)
        return json_output

    def gen_hash(self, serialized_doc):
        return hashlib.sha512(serialized_doc.encode('utf-8')).hexdigest()
