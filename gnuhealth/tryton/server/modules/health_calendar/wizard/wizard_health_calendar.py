# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
# SPDX-FileCopyrightText: 2014 Sebastian Marro <smarro@thymbra.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                       HEALTH CALENDAR PACKAGE                         # 
#               wizard_health_calendar: main wizard file                #
#########################################################################

from datetime import timedelta, datetime, time
import pytz
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, StateTransition, \
    Button
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.modules.health.core import get_institution

__all__ = ['CreateAppointmentStart', 'CreateAppointment']

from ..exceptions import (
    NoCompanyTimezone,
    EndDateBeforeStart,
    PeriodTooLong
    )


class CreateAppointmentStart(ModelView):
    'Create Appointments Start'
    __name__ = 'gnuhealth.calendar.create.appointment.start'

    healthprof = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health Prof',
        required=True)
    specialty = fields.Many2One(
        'gnuhealth.specialty', 'Specialty',
        required=True)
    institution = fields.Many2One(
        'gnuhealth.institution', 'Institution',
        required=True)
    date_start = fields.Date('Start Date', required=True)
    date_end = fields.Date('End Date', required=True)
    time_start = fields.Time('Start Time', required=True, format='%H:%M')
    time_end = fields.Time('End Time', required=True, format='%H:%M')
    appointment_minutes = fields.Integer('Appointment Minutes', required=True)
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')

    @staticmethod
    def default_institution():
        return get_institution()

    @fields.depends('healthprof')
    def on_change_with_specialty(self):
        # Return the Current / Main speciality of the Health Professional
        # if this speciality has been specified in the HP record.
        if (self.healthprof and self.healthprof.main_specialty):
            specialty = self.healthprof.main_specialty.specialty.id
            return specialty


class CreateAppointment(Wizard):
    'Create Appointment'
    __name__ = 'gnuhealth.calendar.create.appointment'

    start = StateView(
        'gnuhealth.calendar.create.appointment.start',
        'health_calendar.create_appointment_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()
    open_ = StateAction('health.action_gnuhealth_appointment_view')

    def transition_create_(self):
        pool = Pool()
        Appointment = pool.get('gnuhealth.appointment')
        Company = pool.get('company.company')

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            company = Company(company_id)
            if company.timezone:
                timezone = pytz.timezone(company.timezone)
            else:
                raise NoCompanyTimezone(
                    gettext('health_calendar.no_company_timezone')
                        )

        appointments = []

        # Iterate over days
        day_count = (self.start.date_end - self.start.date_start).days + 1

        # Validate dates
        if (self.start.date_start and self.start.date_end):
            if (self.start.date_end < self.start.date_start):
                raise EndDateBeforeStart(
                    gettext('health_calendar.msg_end_before_start')
                    )

            if (day_count > 31):
                raise PeriodTooLong(
                    gettext('health_calendar.msg_period_too_long')
                    )

        for single_date in (
            self.start.date_start + timedelta(n)
                for n in range(day_count)):
            if ((single_date.weekday() == 0 and self.start.monday)
                or (single_date.weekday() == 1 and self.start.tuesday)
                or (single_date.weekday() == 2 and self.start.wednesday)
                or (single_date.weekday() == 3 and self.start.thursday)
                or (single_date.weekday() == 4 and self.start.friday)
                or (single_date.weekday() == 5 and self.start.saturday)
                    or (single_date.weekday() == 6 and self.start.sunday)):
                # Iterate over time
                dt = datetime.combine(
                    single_date, self.start.time_start)
                dt = timezone.localize(dt)
                dt = dt.astimezone(pytz.utc)
                dt_end = datetime.combine(
                    single_date, self.start.time_end)
                dt_end = timezone.localize(dt_end)
                dt_end = dt_end.astimezone(pytz.utc)
                while dt < dt_end:
                    appointment = {
                        'healthprof': self.start.healthprof.id,
                        'speciality': self.start.specialty.id,
                        'institution': self.start.institution.id,
                        'appointment_date': dt,
                        'appointment_date_end': dt +
                        timedelta(minutes=self.start.appointment_minutes),
                        'state': 'free',
                        }
                    appointments.append(appointment)
                    dt += timedelta(minutes=self.start.appointment_minutes)
        if appointments:
            Appointment.create(appointments)
        return 'open_'

    def do_open_(self, action):
        action['pyson_domain'] = [
            ('healthprof', '=', self.start.healthprof.id),
            ('appointment_date', '>=',
                datetime.combine(self.start.date_start, time())),
            ('appointment_date', '<=',
                datetime.combine(self.start.date_end, time())),
            ]
        action['pyson_domain'] = PYSONEncoder().encode(action['pyson_domain'])
        action['name'] += ' - %s, %s' % (self.start.healthprof.name.lastname,
                                         self.start.healthprof.name.name)
        return action, {}

    def transition_open_(self):
        return 'end'
