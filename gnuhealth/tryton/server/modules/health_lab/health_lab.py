#!/usr/bin/env python

# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>

# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                     HEALTH LAB package                                #
#                health_lab.py: main module                             #
#########################################################################
from datetime import datetime
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Not, Bool
from trytond.modules.health.core import get_health_professional

__all__ = [
    'PatientData', 'TestType', 'Lab',
    'GnuHealthLabTestUnits', 'GnuHealthTestCritearea',
    'GnuHealthPatientLabTest', 'PatientHealthCondition']


class PatientData(metaclass=PoolMeta):
    __name__ = 'gnuhealth.patient'

    lab_test_ids = fields.One2Many(
        'gnuhealth.patient.lab.test', 'patient_id',
        'Lab Tests Required')


class TestType(ModelSQL, ModelView):
    'Type of Lab test'
    __name__ = 'gnuhealth.lab.test_type'

    name = fields.Char(
        'Test',
        help="Test type, eg X-Ray, hemogram,biopsy...", required=True,
        select=True, translate=True)
    code = fields.Char(
        'Code',
        help="Short name - code for the test", required=True, select=True)
    info = fields.Text('Description')
    product_id = fields.Many2One('product.product', 'Service', required=True)
    critearea = fields.One2Many(
        'gnuhealth.lab.test.critearea', 'test_type_id',
        'Test Cases')

    active = fields.Boolean('Active', select=True)

    @staticmethod
    def default_active():
        return True

    @classmethod
    def __setup__(cls):
        super(TestType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('code_uniq', Unique(t, t.name),
             'The Lab Test code must be unique')
        ]

    @classmethod
    def check_xml_record(cls, records, values):
        return True

    @classmethod
    def search_rec_name(cls, name, clause):
        """ Search for the full name and the code """
        field = None
        for field in ('name', 'code'):
            tests = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if tests:
                break
        if tests:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class Lab(ModelSQL, ModelView):
    'Patient Lab Test Results'
    __name__ = 'gnuhealth.lab'

    name = fields.Char('ID', help="Lab result ID", readonly=True)
    test = fields.Many2One(
        'gnuhealth.lab.test_type', 'Test type',
        help="Lab test type", required=True, select=True)
    source_type = fields.Selection([
        ('patient', 'Patient'),
        ('other_source', 'Other')
        ], 'Source', 
        help='Sample source type.',
        sort=False, select=True)
    source_type_str = source_type.translated('source_type')
    patient = fields.Many2One(
        'gnuhealth.patient', 'Patient',
        states={'invisible': (Eval('source_type') != 'patient')},
        help="Patient ID", select=True)
    other_source = fields.Char('Other', 
        states={'invisible': (Eval('source_type') != 'other_source')},
        help="Other sample source.")
    source_name = fields.Function(
        fields.Text('Source name'), 'get_source_name')

    def get_source_name(self, name=None, with_puid = False, with_gender = False):
        if self.is_patient():
            pname = self.patient and self.patient.rec_name or ''
            puid_str = with_puid and self.patient and f' ({self.patient.puid})' or ''
            gender_str = with_gender and self.patient and f' {self.patient.gender_str}' or ''
            return pname + puid_str + gender_str
        else:
            return (self.other_source or '')

    pathologist = fields.Many2One(
        'gnuhealth.healthprofessional', 'Pathologist',
        help="Pathologist", select=True)
    requestor = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health prof',
        help="Doctor who requested the test", select=True)
    results = fields.Text('Results')
    diagnosis = fields.Text('Diagnosis')
    critearea = fields.One2Many(
        'gnuhealth.lab.test.critearea',
        'gnuhealth_lab_id', 'Lab Test Critearea')
    date_requested = fields.DateTime(
        'Date requested', required=True, select=True)
    date_analysis = fields.DateTime('Date of the Analysis', select=True)
    request_order = fields.Integer('Order', readonly=True)

    pathology = fields.Many2One(
        'gnuhealth.pathology', 'Pathology',
        help='Pathology confirmed / associated to this lab test.')

    analytes_summary = fields.Function(
        fields.Text('Summary'), 'get_analytes_summary')

    def get_analytes_summary(self, name):
        summ = ""
        for analyte in self.critearea:
            if analyte.result or analyte.result_text:
                res = ""
                res_text = ""
                if analyte.result_text:
                    res_text = analyte.result_text
                if analyte.result:
                    res = str(analyte.result) + \
                        " (" + analyte.units.name + ")  "
                summ = summ + analyte.rec_name + "  " + \
                    res + res_text + "\n"
        return summ

    @classmethod
    def __setup__(cls):
        super(Lab, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('id_uniq', Unique(t, t.name),
             'The test ID code must be unique')
        ]
        cls._order.insert(0, ('date_requested', 'DESC'))
        cls._buttons.update({'complete_criteareas': {}})

    @staticmethod
    def default_date_requested():
        return datetime.now()

    @staticmethod
    def default_date_analysis():
        return datetime.now()

    @staticmethod
    def default_source_type():
        return 'patient'

    @classmethod
    def generate_code(cls, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'lab_test_sequence', **pattern)
        if sequence:
            return sequence.get()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('name'):
                values['name'] = cls.generate_code()

        return super(Lab, cls).create(vlist)

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [
            bool_op,
            ('patient', ) + tuple(clause[1:]),
            ('name', ) + tuple(clause[1:]),
            ]

    @classmethod
    @ModelView.button
    def complete_criteareas(cls, labs):
        pool = Pool()
        Critearea = pool.get('gnuhealth.lab.test.critearea')

        lab = labs[0]
        test_cases = []

        for critearea in (lab and lab.test and lab.test.critearea):
            test_cases.append({
                'gnuhealth_lab_id': lab.id,
                'name': critearea.name,
                'code': critearea.code,
                'sequence': critearea.sequence,
                'lower_limit': critearea.lower_limit,
                'upper_limit': critearea.upper_limit,
                'normal_range': critearea.normal_range,
                'units': critearea.units and critearea.units.id})

        if test_cases:
            Critearea.create(test_cases)

    def is_patient(self):
        return (self.source_type == 'patient')

    def is_other_source(self):
        return (self.source_type == 'other_source')
        

class GnuHealthLabTestUnits(ModelSQL, ModelView):
    'Lab Test Units'
    __name__ = 'gnuhealth.lab.test.units'

    name = fields.Char('Unit', select=True)
    code = fields.Char('Code', select=True)

    @classmethod
    def __setup__(cls):
        super(GnuHealthLabTestUnits, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_uniq', Unique(t, t.name),
             'The Unit name must be unique')
        ]

    @classmethod
    def check_xml_record(cls, records, values):
        return True


class GnuHealthTestCritearea(ModelSQL, ModelView):
    'Lab Test Critearea'
    __name__ = 'gnuhealth.lab.test.critearea'

    name = fields.Char(
        'Analyte', required=True, select=True,
        translate=True)
    excluded = fields.Boolean(
        'Excluded', help='Select this option when'
        ' this analyte is excluded from the test')
    result = fields.Float('Value')
    result_text = fields.Char(
        'Result - Text', help='Non-numeric results. For '
        'example qualitative values, morphological, colors ...')
    remarks = fields.Char('Remarks')
    normal_range = fields.Text('Reference')
    lower_limit = fields.Float('Lower Limit')
    upper_limit = fields.Float('Upper Limit')
    warning = fields.Boolean(
        'Warn', help='Warns the patient about this '
        ' analyte result'
        ' It is useful to contextualize the result to each patient status '
        ' like age, sex, comorbidities, ...')
    units = fields.Many2One('gnuhealth.lab.test.units', 'Units')
    test_type_id = fields.Many2One(
        'gnuhealth.lab.test_type', 'Test type',
        select=True)
    gnuhealth_lab_id = fields.Many2One(
        'gnuhealth.lab', 'Test Cases',
        select=True)
    sequence = fields.Integer('Sequence')

    ## code field is mainly used by interface script, for example:
    ## gnuhealth_csv_lab_interface.py in example directory.
    ##
    ## sequence field is not suitable for interface script, for it may
    ## be changed by user for sort reason, when it changed, interface
    ## script can not find error. for example: when a criterea
    ## sequence is changed from 1 to 2 for sort reason. if interface
    ## script do not update, it will run no error and push wrong
    ## value.
    ##
    ## name field is not suitable for interface stript too, for it
    ## will be changed when user use different languages.
    code = fields.Char('Code', select=True, translate=False,
                       help="Lab test critearea code, mainly used by lab interface script.")
    
    # Show the warning icon if warning is active on the analyte line
    lab_warning_icon = fields.Function(fields.Char(
        'Lab Warning Icon'),
        'get_lab_warning_icon')

    def get_lab_warning_icon(self, name):
        if (self.warning):
            return 'gnuhealth-warning'

    @classmethod
    def __setup__(cls):
        super(GnuHealthTestCritearea, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_sequence():
        return 1

    @staticmethod
    def default_excluded():
        return False

    @fields.depends('result', 'lower_limit', 'upper_limit')
    def on_change_with_warning(self):
        if (self.result and self.lower_limit):
            if (self.result < self.lower_limit):
                return True

        if (self.result and self.upper_limit):
            if (self.result > self.upper_limit):
                return True

    @classmethod
    def check_xml_record(cls, records, values):
        return True


class GnuHealthPatientLabTest(ModelSQL, ModelView):
    'Lab Test Request'
    __name__ = 'gnuhealth.patient.lab.test'

    name = fields.Many2One(
        'gnuhealth.lab.test_type', 'Test Type',
        required=True, select=True)
    date = fields.DateTime('Date', select=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('tested', 'Tested'),
        ('ordered', 'Ordered'),
        ('cancel', 'Cancel'),
        ], 'State', readonly=True, select=True)
    source_type = fields.Selection([
        ('patient', 'Patient'),
        ('other_source', 'Other')
        ], 'Source', 
        help='Sample source type.',
        sort=False, select=True)
    patient_id = fields.Many2One(
        'gnuhealth.patient', 'Patient',
        states={'invisible': (Eval('source_type') != 'patient')},
        select=True)
    other_source = fields.Char('Other', 
        states={'invisible': (Eval('source_type') != 'other_source')},
        help="Other sample source.")
    source_name = fields.Function(
        fields.Text('Source name'), 'get_source_name')

    def get_source_name(self, name):
        if self.is_patient():
            return self.patient_id and self.patient_id.rec_name or ''
        else:
            return (self.other_source or '')

    doctor_id = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health prof.',
        help="Health professional who requests the lab test.", select=True)
    context = fields.Many2One(
        'gnuhealth.pathology', 'Context',
        help="Health context for this order. It can be a suspected or"
             " existing health condition, a regular health checkup, ...",
             select=True)
    request = fields.Integer('Order', readonly=True)
    urgent = fields.Boolean('Urgent')

    @classmethod
    def __setup__(cls):
        super(GnuHealthPatientLabTest, cls).__setup__()
        cls._order.insert(0, ('date', 'DESC'))
        cls._order.insert(1, ('request', 'DESC'))
        cls._order.insert(2, ('name', 'ASC'))

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_source_type():
        return 'patient'

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_doctor_id():
        return get_health_professional()

    @classmethod
    def generate_code(cls, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'lab_request_sequence', **pattern)
        if sequence:
            return sequence.get()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('name'):
                values['name'] = cls.generate_code()

        return super(GnuHealthPatientLabTest, cls).create(vlist)

    @classmethod
    def copy(cls, tests, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['request'] = None
        default['date'] = cls.default_date()
        return super(GnuHealthPatientLabTest, cls).copy(
            tests, default=default)

    def is_patient(self):
        return (self.source_type == 'patient')

    def is_other_source(self):
        return (self.source_type == 'other_source')


class PatientHealthCondition(metaclass=PoolMeta):
    __name__ = 'gnuhealth.patient.disease'

    # Adds lab confirmed and the link to the test to the
    # Patient health Condition

    lab_confirmed = fields.Boolean(
        'Lab Confirmed', help='Confirmed by'
        ' laboratory test')

    lab_test = fields.Many2One(
        'gnuhealth.lab', 'Lab Test',
        domain=[('patient', '=', Eval('name'))], depends=['name'],
        states={'invisible': Not(Bool(Eval('lab_confirmed')))},
        help='Lab test that confirmed the condition')
