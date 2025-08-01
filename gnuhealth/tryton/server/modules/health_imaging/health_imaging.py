#!/usr/bin/env python

# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
# SPDX-FileCopyrightText: 2013 Sebastián Marró <smarro@thymbra.com>

# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                     HEALTH IMAGING package                            #
#                 health_imaging.pu: Main module                        #
#########################################################################
from datetime import datetime
from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.pyson import Eval
from trytond.pool import Pool

from trytond.modules.health.core import (
    get_health_professional, compute_age_from_dates)

__all__ = [
    'ImagingTestType',
    'ImagingTest', 'ImagingTestRequest', 'ImagingTestResult']


class ImagingTestType(ModelSQL, ModelView):
    'Medical Imaging Study Type'
    __name__ = 'gnuhealth.imaging.test.type'

    code = fields.Char(
        'Code', required=True,
        help="Suggest use values of DICOM "
        "Modality (0008,0060) tag.")
    name = fields.Char(
        'Name', required=True, translate=True,
        help="Suggest use descriptions of DICOM "
        "Modality (0008,0060) tag.")


class ImagingTest(ModelSQL, ModelView):
    'Medical Imaging Study'
    __name__ = 'gnuhealth.imaging.test'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True, translate=True)
    test_type = fields.Many2One(
        'gnuhealth.imaging.test.type', 'Type',
        required=True)
    product = fields.Many2One('product.product', 'Product', required=True)

    active = fields.Boolean('Active', select=True)

    @staticmethod
    def default_active():
        return True


class ImagingTestRequest(Workflow, ModelSQL, ModelView):
    'Medical Imaging Study Request'
    __name__ = 'gnuhealth.imaging.test.request'

    def get_rec_name(self, name):
        res = ''
        if self.urgent:
            res = '**Urgent**'
        if self.doctor:
            res = f'{res} ({self.doctor.rec_name}) //'
        if self.context:
            res = f'{res} CONTEXT: {self.context.rec_name}'
        return res

    patient = fields.Many2One('gnuhealth.patient', 'Patient', required=True)
    date = fields.DateTime('Date', required=True)
    requested_test = fields.Many2One(
        'gnuhealth.imaging.test', 'Study',
        required=True)
    doctor = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health prof', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('done', 'Done'),
        ], 'State', readonly=True)

    context = fields.Many2One(
        'gnuhealth.pathology', 'Context',
        help="Health context for this order. It can be a suspected or"
             " existing health condition, a regular health checkup, ...",
             select=True)

    comment = fields.Text('Additional Information')
    request = fields.Char('Order', readonly=True)
    request_line = fields.Char('Order line', readonly=True)
    urgent = fields.Boolean('Urgent')

    @classmethod
    def __setup__(cls):
        super(ImagingTestRequest, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'requested'),
            ('requested', 'done')
        ))
        cls._buttons.update({
            'requested': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            'generate_results': {
                'invisible': ~Eval('state').in_(['requested'])
                }
            })
        cls._order.insert(0, ('date', 'DESC'))
        cls._order.insert(1, ('request', 'DESC'))

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_doctor():
        return get_health_professional()

    @classmethod
    def generate_code(cls, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'imaging_req_seq', **pattern)
        if sequence:
            return sequence.get()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        count = len(vlist)
        num = 1
        for values in vlist:
            if not values.get('request'):
                values['request'] = cls.generate_code()
            if not values.get('request_line'):
                values['request_line'] = f'{values["request"]}-{count:02}-{num:02}'
            num = num + 1

        return super(ImagingTestRequest, cls).create(vlist)

    @classmethod
    def copy(cls, tests, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['request'] = None
        default['request_line'] = None
        default['date'] = cls.default_date()
        return super(ImagingTestRequest, cls).copy(tests, default=default)

    @classmethod
    @ModelView.button
    @Workflow.transition('requested')
    def requested(cls, requests):
        pass

    @classmethod
    @ModelView.button_action('health_imaging.wizard_generate_result')
    def generate_results(cls, requests):
        pass

    @classmethod
    @Workflow.transition('done')
    def done(cls, requests):
        pass


class ImagingTestResult(ModelSQL, ModelView):
    'Medical Imaging Study Result'
    __name__ = 'gnuhealth.imaging.test.result'

    def patient_age_at_evaluation(self, name):
        if (self.patient.name.dob and self.date):
            return compute_age_from_dates(
                self.patient.name.dob, None, None, None, 'age',
                self.date.date())

    patient = fields.Many2One('gnuhealth.patient', 'Patient', readonly=True)
    number = fields.Char('Number', readonly=True)
    date = fields.DateTime('Date', required=True)
    request_date = fields.DateTime('Requested Date', readonly=True)
    requested_test = fields.Many2One(
        'gnuhealth.imaging.test', 'Study',
        required=True)
    request = fields.Many2One(
        'gnuhealth.imaging.test.request', 'Request Info',
        readonly=True)
    order = fields.Char(
        'Order', readonly=True,
        help="The order ID containing this particular imaging study")
    doctor = fields.Many2One(
        'gnuhealth.healthprofessional', 'Evaluated by', required=True)

    computed_age = fields.Function(fields.Char(
            'Age',
            help="Computed patient age at the moment of the evaluation"),
            'patient_age_at_evaluation')

    comment = fields.Text('Additional Information')
    images = fields.One2Many('ir.attachment', 'resource', 'Images')

    @classmethod
    def generate_code(cls, **pattern):
        Config = Pool().get('gnuhealth.sequences')
        config = Config(1)
        sequence = config.get_multivalue(
            'imaging_test_sequence', **pattern)
        if sequence:
            return sequence.get()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('number'):
                values['number'] = cls.generate_code()
        return super(ImagingTestResult, cls).create(vlist)

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [
            bool_op,
            ('patient',) + tuple(clause[1:]),
            ('number',) + tuple(clause[1:]),
            ]

    @classmethod
    def __setup__(cls):
        super(ImagingTestResult, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('number_uniq', Unique(t, t.number),
             'The study ID code must be unique')
        ]
        cls._order.insert(0, ('date', 'DESC'))

    def get_rec_name(self, name):
        res = f'{self.number} ({self.requested_test.name})'
        return res
