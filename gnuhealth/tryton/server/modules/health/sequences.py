# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                           HEALTH package                              #
#                sequences.py: HMIS sequences for this package          #
#########################################################################

from trytond.model import (ModelView, ModelSingleton, ModelSQL,
                           ValueMixin, MultiValueMixin, fields)
from trytond import backend
from trytond.pyson import Id
from trytond.pool import Pool
from trytond.tools.multivalue import migrate_property

# Sequences
# The patient_sequence is no longer used
# The patient ID is taken from the person demographics
patient_sequence = fields.Many2One(
    'ir.sequence', 'Patient Sequence', required=True,
    domain=[('sequence_type', '=', Id(
        'health', 'seq_type_gnuhealth_patient'))])

patient_evaluation_sequence = fields.Many2One(
    'ir.sequence', 'Patient Evaluation Sequence', required=True,
    domain=[('sequence_type', '=', Id(
        'health', 'seq_type_gnuhealth_patient_evaluation'))])

appointment_sequence = fields.Many2One(
    'ir.sequence', 'Appointment Sequence', required=True,
    domain=[('sequence_type', '=', Id(
        'health', 'seq_type_gnuhealth_appointment'))])


prescription_sequence = fields.Many2One(
    'ir.sequence', 'Prescription Sequence', required=True,
    domain=[('sequence_type', '=', Id(
        'health', 'seq_type_gnuhealth_prescription'))])


# GNU HEALTH SEQUENCES
class GnuHealthSequences(ModelSingleton, ModelSQL, ModelView, MultiValueMixin):
    'Standard Sequences for GNU Health'
    __name__ = 'gnuhealth.sequences'

    patient_sequence = fields.MultiValue(
        patient_sequence)

    patient_evaluation_sequence = fields.MultiValue(
        patient_evaluation_sequence)

    appointment_sequence = fields.MultiValue(
        appointment_sequence)

    prescription_sequence = fields.MultiValue(
        prescription_sequence)

    @classmethod
    def default_patient_sequence(cls, **pattern):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('health',
                                    'seq_gnuhealth_patient')
        except KeyError:
            return None

    @classmethod
    def default_patient_evaluation_sequence(cls, **pattern):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('health',
                                    'seq_gnuhealth_patient_evaluation')
        except KeyError:
            return None

    @classmethod
    def default_appointment_sequence(cls, **pattern):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('health',
                                    'seq_gnuhealth_appointment')
        except KeyError:
            return None

    @classmethod
    def default_prescription_sequence(cls, **pattern):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('health',
                                    'seq_gnuhealth_prescription')
        except KeyError:
            return None


class _ConfigurationValue(ModelSQL):

    _configuration_value_field = None

    @classmethod
    def __register__(cls, module_name):
        exist = backend.TableHandler.table_exist(cls._table)

        super(_ConfigurationValue, cls).__register__(module_name)

        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append(cls._configuration_value_field)
        value_names.append(cls._configuration_value_field)
        migrate_property(
            'gnuhealth.sequences', field_names, cls, value_names,
            fields=fields)


class PatientSequence(_ConfigurationValue, ModelSQL, ValueMixin):
    'Patient Sequences setup'
    __name__ = 'gnuhealth.sequences.patient_sequence'
    patient_sequence = patient_sequence
    _configuration_value_field = 'patient_sequence'

    @classmethod
    def check_xml_record(cls, records, values):
        return True


class PatientEvaluationSequence(_ConfigurationValue, ModelSQL, ValueMixin):
    'Patient Evaluation Sequence setup'
    __name__ = 'gnuhealth.sequences.patient_evaluation_sequence'
    patient_evaluation_sequence = patient_evaluation_sequence
    _configuration_value_field = 'patient_evaluation_sequence'

    @classmethod
    def check_xml_record(cls, records, values):
        return True


class AppointmentSequence(_ConfigurationValue, ModelSQL, ValueMixin):
    'Appointment Sequence setup'
    __name__ = 'gnuhealth.sequences.appointment_sequence'
    appointment_sequence = appointment_sequence
    _configuration_value_field = 'appointment_sequence'

    @classmethod
    def check_xml_record(cls, records, values):
        return True


class PrescriptionSequence(_ConfigurationValue, ModelSQL, ValueMixin):
    'Prescription Sequence setup'
    __name__ = 'gnuhealth.sequences.prescription_sequence'
    prescription_sequence = prescription_sequence
    _configuration_value_field = 'prescription_sequence'

    @classmethod
    def check_xml_record(cls, records, values):
        return True
