# Copyright (C) 2008-2024 Luis Falcon <lfalcon@gnuhealth.org>
# Copyright (C) 2013  Sebastián Marro <smarro@thymbra.com>
# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateAction, StateTransition, StateView, \
    Button
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool

from trytond.modules.health.core import get_health_professional

__all__ = ['WizardGenerateResult', 'RequestImagingTest',
    'RequestPatientImagingTestStart', 'RequestPatientImagingTest']


class WizardGenerateResult(Wizard):
    'Generate Results'
    __name__ = 'wizard.generate.result'
    start_state = 'open_'
    open_ = StateAction('health_imaging.act_imaging_test_result_view')

    def do_open_(self, action):
        pool = Pool()
        Request = pool.get('gnuhealth.imaging.test.request')
        Result = pool.get('gnuhealth.imaging.test.result')

        request_data = []
        requests = Request.browse(Transaction().context.get('active_ids'))
        for request in requests:
            request_data.append({
                'patient': request.patient.id,
                'date': datetime.now(),
                'request_date': request.date,
                'requested_test': request.requested_test,
                'request': request.id,
                'order': request.request,
                'doctor': request.doctor})
        results = Result.create(request_data)

        action['pyson_domain'] = PYSONEncoder().encode(
            [('id', 'in', [r.id for r in results])])

        Request.requested(requests)
        Request.done(requests)
        return action, {}


class RequestImagingTest(ModelView):
    'Request - Test'
    __name__ = 'gnuhealth.request-imaging-test'
    _table = 'gnuhealth_request_imaging_test'

    request = fields.Many2One('gnuhealth.patient.imaging.test.request.start',
        'Request', required=True)
    test = fields.Many2One('gnuhealth.imaging.test', 'Study', required=True)


class RequestPatientImagingTestStart(ModelView):
    'Request Patient Imaging Test Start'
    __name__ = 'gnuhealth.patient.imaging.test.request.start'

    date = fields.DateTime('Date')
    patient = fields.Many2One('gnuhealth.patient', 'Patient', required=True)
    doctor = fields.Many2One('gnuhealth.healthprofessional', 'Health prof',
        required=True, help="Health professionalwho requests the study.")
    context = fields.Many2One('gnuhealth.pathology', 'Context',
        help="Health context for this order. It can be a suspected or"
             " existing health condition, a regular health checkup, ...",
             select=True)
    tests = fields.Many2Many('gnuhealth.request-imaging-test', 'request',
        'test', 'Tests', required=True)
    urgent = fields.Boolean('Urgent')

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_patient():
        if Transaction().context.get('active_model') == 'gnuhealth.patient':
            return Transaction().context.get('active_id')

    @staticmethod
    def default_doctor():
        return get_health_professional()

class RequestPatientImagingTest(Wizard):
    'Request Patient Imaging Test'
    __name__ = 'gnuhealth.patient.imaging.test.request'

    start = StateView('gnuhealth.patient.imaging.test.request.start',
        'health_imaging.patient_imaging_test_request_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Request', 'request', 'tryton-ok', default=True),
            ])
    request = StateTransition()

    def generate_code(self, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'imaging_req_seq', **pattern)
        if sequence:
            return sequence.get()


    def transition_request(self):
        ImagingTestRequest = Pool().get('gnuhealth.imaging.test.request')
        request_number = self.generate_code()
        imaging_tests = []
        count = len(self.start.tests)
        num = 1
        for test in self.start.tests:
            imaging_test = {}
            imaging_test['request'] = request_number
            imaging_test['request_line'] = f'{request_number}-{count:02}-{num:02}'
            imaging_test['requested_test'] = test.id
            imaging_test['patient'] = self.start.patient.id
            if self.start.doctor:
                imaging_test['doctor'] = self.start.doctor.id
            if self.start.context:
                imaging_test['context'] = self.start.context.id

            imaging_test['date'] = self.start.date
            imaging_test['urgent'] = self.start.urgent
            imaging_tests.append(imaging_test)
            num = num + 1
        ImagingTestRequest.create(imaging_tests)

        return 'end'
