# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.pyson import Eval, Not, Bool
from trytond.i18n import gettext
from ..exceptions import LabOrderExists

__all__ = [
    'CreateLabTestOrderInit', 'CreateLabTestOrder', 'RequestTest',
    'RequestPatientLabTestStart', 'RequestPatientLabTest']


from trytond.modules.health.core import get_health_professional


class CreateLabTestOrderInit(ModelView):
    'Create Test Report Init'
    __name__ = 'gnuhealth.lab.test.create.init'


class CreateLabTestOrder(Wizard):
    'Create Lab Test Report'
    __name__ = 'gnuhealth.lab.test.create'

    start = StateView(
        'gnuhealth.lab.test.create.init',
        'health_lab.view_lab_make_test', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create Test Order', 'create_lab_test', 'tryton-ok', True),
            ])

    create_lab_test = StateTransition()

    def transition_create_lab_test(self):
        TestRequest = Pool().get('gnuhealth.patient.lab.test')
        Lab = Pool().get('gnuhealth.lab')

        tests_report_data = []

        tests = TestRequest.browse(Transaction().context.get('active_ids'))

        for lab_test_order in tests:

            test_cases = []
            test_report_data = {}

            if lab_test_order.state == 'ordered':
                raise LabOrderExists(
                    gettext('health_lab.msg_lab_order_exists')
                    )

            test_report_data['test'] = lab_test_order.name.id
            test_report_data['source_type'] = lab_test_order.source_type
            test_report_data['patient'] = lab_test_order.patient_id and lab_test_order.patient_id.id
            test_report_data['other_source'] = lab_test_order.other_source
            if lab_test_order.doctor_id:
                test_report_data['requestor'] = lab_test_order.doctor_id.id
            test_report_data['date_requested'] = lab_test_order.date
            test_report_data['request_order'] = lab_test_order.request

            for critearea in lab_test_order.name.critearea:
                test_cases.append(('create', [{
                        'name': critearea.name,
                        'code': critearea.code,
                        'sequence': critearea.sequence,
                        'lower_limit': critearea.lower_limit,
                        'upper_limit': critearea.upper_limit,
                        'normal_range': critearea.normal_range,
                        'units': critearea.units and critearea.units.id,
                    }]))
            test_report_data['critearea'] = test_cases

            tests_report_data.append(test_report_data)

        Lab.create(tests_report_data)
        TestRequest.write(tests, {'state': 'ordered'})

        return 'end'


class RequestTest(ModelView):
    'Request - Test'
    __name__ = 'gnuhealth.request-test'
    _table = 'gnuhealth_request_test'

    request = fields.Many2One(
        'gnuhealth.patient.lab.test.request.start',
        'Request', required=True)
    test = fields.Many2One('gnuhealth.lab.test_type', 'Test', required=True)


class RequestPatientLabTestStart(ModelView):
    'Request Patient Lab Test Start'
    __name__ = 'gnuhealth.patient.lab.test.request.start'

    date = fields.DateTime('Date')
    source_type = fields.Selection([
        ('patient', 'Patient'),
        ('other_source', 'Other')
        ], 'Source', 
        help='Sample source type.',
        sort=False, select=True)
    patient = fields.Many2One('gnuhealth.patient', 
        'Patient',
        states={'invisible': (Eval('source_type') != 'patient')})
    other_source = fields.Char('Other', 
        states={'invisible': (Eval('source_type') != 'other_source')},
        help="Other sample source.")
    context = fields.Many2One(
        'gnuhealth.pathology', 'Context',
        help="Health context for this order. It can be a suspected or"
             " existing health condition, a regular health checkup, ...")
    doctor = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health prof',
        help="Health professional who ordered the lab tests.")
    tests = fields.Many2Many(
        'gnuhealth.request-test', 'request', 'test',
        'Tests', required=True)
    urgent = fields.Boolean('Urgent')

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_source_type():
        return 'patient'

    @staticmethod
    def default_patient():
        if Transaction().context.get('active_model') == 'gnuhealth.patient':
            return Transaction().context.get('active_id')

    @staticmethod
    def default_doctor():
        return get_health_professional()


class RequestPatientLabTest(Wizard):
    'Request Patient Lab Test'
    __name__ = 'gnuhealth.patient.lab.test.request'

    start = StateView(
        'gnuhealth.patient.lab.test.request.start',
        'health_lab.patient_lab_test_request_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Request', 'request', 'tryton-ok', default=True),
            ])
    request = StateTransition()

    def generate_code(self, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'lab_request_sequence', **pattern)
        if sequence:
            return sequence.get()

    def transition_request(self):
        PatientLabTest = Pool().get('gnuhealth.patient.lab.test')
        request_number = self.generate_code()
        lab_tests = []
        for test in self.start.tests:
            lab_test = {}
            lab_test['request'] = request_number
            lab_test['name'] = test.id
            lab_test['source_type'] = self.start.source_type
            lab_test['patient_id'] = self.start.patient and self.start.patient.id
            lab_test['other_source'] = self.start.other_source
            if self.start.doctor:
                lab_test['doctor_id'] = self.start.doctor.id
            if self.start.context:
                lab_test['context'] = self.start.context.id
            lab_test['date'] = self.start.date
            lab_test['urgent'] = self.start.urgent
            lab_tests.append(lab_test)
        PatientLabTest.create(lab_tests)

        return 'end'
