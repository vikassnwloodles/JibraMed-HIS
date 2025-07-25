# Copyright (C) 2008-2024 Luis Falcon <falcon@gnuhealth.org>
# Copyright (C) 2011-2024 GNU Solidario <health@gnusolidario.org>
# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from collections import defaultdict
from sql.aggregate import Count
from sql.functions import DateTrunc
from datetime import date, datetime
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.modules.health.core import parse_compute_age
from dateutil.relativedelta import relativedelta

from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib as mpl

from trytond.modules.health.core import (convert_date_timezone,
                                         matplotlib_setup)
from trytond.i18n import gettext

import io

__all__ = ['InstitutionEpidemicsReport']


class InstitutionEpidemicsReport(Report):
    __name__ = 'gnuhealth.epidemics.report'

    @classmethod
    def get_population_with_no_dob(cls):
        """ Return Total Number of living people in the system
        without a date of birth"""
        pool = Pool()
        Party = pool.get('party.party')

        return Party.search([
                ('is_person', '=', True),
                ('deceased', '!=', True),
                ('dob', '=', None),
                ], count=True)

    @classmethod
    def get_population(cls, date1, date2, gender, total):
        """ Return Total Number of living people in the system
        segmented by age group and gender"""
        pool = Pool()
        Party = pool.get('party.party')

        domain = [
            ('deceased', '!=', True),
            ('gender', '=', gender),
            ]

        if not total:
            domain.append(('dob', '>=', date2))
            domain.append(('dob', '<=', date1))

        return Party.search(domain, count=True)

    @classmethod
    def get_new_people(cls, start_date, end_date, in_health_system):
        """ Return Total Number of new registered persons alive """
        pool = Pool()
        Party = pool.get('party.party')

        domain = [
            ('activation_date', '>=', start_date),
            ('activation_date', '<=', end_date),
            ('deceased', '!=', True),
            ('is_person', '=', True),
            ]

        if in_health_system:
            domain.append(('is_patient', '=', True))

        return Party.search(domain, count=True)

    @classmethod
    def get_new_births(cls, start_date, end_date):
        """ Return birth certificates within that period """
        pool = Pool()
        BirthCertificate = pool.get('gnuhealth.birth_certificate')

        return BirthCertificate.search([
                ('dob', '>=', start_date),
                ('dob', '<=', end_date),
                ], count=True)

    @classmethod
    def get_new_deaths(cls, start_date, end_date):
        """ Return death certificates within that period """
        """ Truncate the timestamp of DoD to match a whole day"""
        pool = Pool()
        DeathCertificate = pool.get('gnuhealth.death_certificate')
        table = DeathCertificate.__table__()

        dod = DateTrunc('day', table.dod)

        cursor = Transaction().connection.cursor()
        cursor.execute(*table.select(
                Count(table.dod),
                where=((dod >= start_date) & (dod <= end_date))))
        return cursor.fetchone()

    @classmethod
    def get_confirmed_cases(cls, start_date, end_date, dx):
        """ Return number of confirmed cases """

        Condition = Pool().get('gnuhealth.patient.disease')

        clause = [
            ('diagnosed_date', '>=', start_date),
            ('diagnosed_date', '<=', end_date),
            ]

        if dx:
            clause.append(('pathology', '=', dx))

        res = Condition.search(clause)

        return(res)

    @classmethod
    def get_epi_by_day(cls, start_date, end_date, dx):
        """ Return number of confirmed cases """

        Condition = Pool().get('gnuhealth.patient.disease')

        current_day = start_date
        aggr = []
        while current_day <= end_date:
            current_day = current_day + relativedelta(days=1)

            clause = [
                ('diagnosed_date', '=', current_day),
                ]

            if dx:
                clause.append(('pathology', '=', dx))

            res = Condition.search(clause)
            cases_day = len(res)
            daily_data = {'date': current_day, 'cases': cases_day}
            aggr.append(daily_data)
        return(aggr)

    # Death Certificates by day
    @classmethod
    def get_deaths_by_day(cls, start_date, end_date, dx):
        """ Return number of death related to the condition
            Includes both the ultimate case as well as those
            certificates that have the condition as a leading cause
        """

        DeathCert = Pool().get('gnuhealth.death_certificate')

        current_day = start_date
        aggr = []
        while current_day <= end_date:
            cur_day_time = datetime.combine((current_day), datetime.min.time())

            utc_from = convert_date_timezone(cur_day_time, 'utc')
            utc_to = convert_date_timezone(cur_day_time +
                                           relativedelta(days=1), 'utc')

            clause = [
                ('dod', '>=', utc_from),
                ('dod', '<', utc_to)
                ]

            res = DeathCert.search(clause)

            # Reset the cases for each day
            as_immediate_cause = 0
            as_underlying_condition = 0

            # Get the immediate cause of death and the underlying conditions
            # for each certificate on each day.

            for cert in res:
                if (cert.cod.id == dx):
                    as_immediate_cause = as_immediate_cause + 1
                for underlying_condition in cert.underlying_conditions:
                    if (underlying_condition.condition.id == dx):
                        as_underlying_condition = as_underlying_condition + 1

            daily_data = {'date': current_day,
                          'certs_day_ic': as_immediate_cause,
                          'certs_day_uc': as_underlying_condition}
            aggr.append(daily_data)
            current_day = current_day + relativedelta(days=1)

        return(aggr)

    @classmethod
    def plot_cases_timeseries(cls, start_date, end_date,
                              health_condition_id, hc):

        epi_series = cls.get_epi_by_day(start_date,
                                        end_date, health_condition_id)

        days = []
        cases_day = []
        for day in epi_series:
            days.append(day['date'])
            # Confirmed cases by day
            cases_day.append(day['cases'])

        fig = plt.figure(figsize=(6, 3))
        cases_by_day = fig.add_subplot(1, 1, 1)
        cases_by_day.bar(days, cases_day)
        cases_by_day.yaxis.set_major_locator(MaxNLocator(integer=True))
        fig.autofmt_xdate()

        holder = io.BytesIO()
        fig.savefig(holder, format="svg")
        image = holder.getvalue()

        holder.close()
        return (image)

    @classmethod
    def plot_deaths_timeseries(cls, start_date,
                               end_date, health_condition_id, hc):

        death_certs = cls.get_deaths_by_day(start_date,
                                            end_date, health_condition_id)

        days = []
        certs_ic_day = []
        certs_uc_day = []
        for day in death_certs:
            days.append(day['date'])
            # Death certificates as an immediate cause
            certs_ic_day.append(day['certs_day_ic'])
            # Death certificates as an underlying cause
            certs_uc_day.append(day['certs_day_uc'])

        fig = plt.figure(figsize=(6, 3))
        deaths_by_day = fig.add_subplot(1, 1, 1)
        deaths_by_day.plot(days, certs_ic_day,
                           label=gettext("health_reporting.msg_plot_label_immediate_cause_str"))
        deaths_by_day.plot(days, certs_uc_day,
                           label=gettext("health_reporting.msg_plot_label_underlying_condition_str"))
        deaths_by_day.yaxis.set_major_locator(MaxNLocator(integer=True))
        deaths_by_day.legend()

        fig.autofmt_xdate()

        holder = io.BytesIO()
        fig.savefig(holder, format="svg")
        image = holder.getvalue()

        holder.close()
        return (image)

    @classmethod
    def plot_cases_ethnicity(cls, start_date, end_date, ethnic_count, hc):

        for k, v in list(ethnic_count.items()):
            if (v == 0):
                # Remove ethnicities with zero cases from the plot
                del(ethnic_count[k])

        fig = plt.figure(figsize=(6, 3))
        cases_by_ethnicity = fig.add_subplot(1, 1, 1)
        cases_by_ethnicity.pie(ethnic_count.values(),
                               autopct='%1.1f%%',
                               labels=ethnic_count.keys())

        fig.autofmt_xdate()

        holder = io.BytesIO()
        fig.savefig(holder, format="svg")
        image = holder.getvalue()

        holder.close()
        return (image)

    @classmethod
    def get_ethnic_groups(cls):
        # Build a list with the ethnic groups
        Condition = Pool().get('gnuhealth.ethnicity')
        ethnic_groups = Condition.search([])
        ethnicities = []
        for ethnic_group in ethnic_groups:
            ethnicities.append(ethnic_group.name)
        return (ethnicities)

    @classmethod
    def plot_cases_socioeconomics(cls, start_date, end_date, ses_count, hc):

        for k, v in list(ses_count.items()):
            if (v == 0):
                # Remove socioeconomic groups with zero cases from the plot
                del(ses_count[k])

        fig = plt.figure(figsize=(6, 3))
        cases_by_socioeconomics = fig.add_subplot(1, 1, 1)
        cases_by_socioeconomics.pie(ses_count.values(),
                                    autopct='%1.1f%%',
                                    labels=ses_count.keys())

        fig.autofmt_xdate()

        holder = io.BytesIO()
        fig.savefig(holder, format="svg")
        image = holder.getvalue()

        holder.close()
        return (image)

    @classmethod
    def get_context(cls, records, header, data):

        Condition = Pool().get('gnuhealth.pathology')

        ethnic_groups = cls.get_ethnic_groups()

        ethnic_count = defaultdict(int)

        ses_count = defaultdict(int)

        context = super(InstitutionEpidemicsReport, cls).get_context(
            records, header, data)

        start_date = data['start_date']
        context['start_date'] = data['start_date']

        end_date = data['end_date']
        context['end_date'] = data['end_date']

        context['demographics'] = data['demographics']

        health_condition_id = data['health_condition']

        hc = Condition.search(
                [('id', '=', health_condition_id)], limit=1)[0]

        context['health_condition'] = hc

        # Demographics
        today = date.today()

        context[''.join(['p', 'total_', 'f'])] = \
            cls.get_population(None, None, 'f', total=True)

        context[''.join(['p', 'total_', 'm'])] = \
            cls.get_population(None, None, 'm', total=True)

        # Living people with NO date of birth
        context['no_dob'] = \
            cls.get_population_with_no_dob()

        # Build the Population Pyramid for registered people

        for age_group in range(0, 21):
            date1 = today - relativedelta(years=(age_group*5))
            date2 = today - relativedelta(years=((age_group*5)+5), days=-1)

            context[''.join(['p', str(age_group), 'f'])] = \
                cls.get_population(date1, date2, 'f', total=False)
            context[''.join(['p', str(age_group), 'm'])] = \
                cls.get_population(date1, date2, 'm', total=False)

        # Count those lucky over 105 years old :)
        date1 = today - relativedelta(years=105)
        date2 = today - relativedelta(years=200)

        context['over105f'] = \
            cls.get_population(date1, date2, 'f', total=False)
        context['over105m'] = \
            cls.get_population(date1, date2, 'm', total=False)

        # Count registered people, and those within the system of health
        context['new_people'] = \
            cls.get_new_people(start_date, end_date, False)
        context['new_in_health_system'] = \
            cls.get_new_people(start_date, end_date, in_health_system=True)

        # New births
        context['new_births'] = \
            cls.get_new_births(start_date, end_date)

        # New deaths
        context['new_deaths'] = \
            cls.get_new_deaths(start_date, end_date)

        # Get cases within the specified date range

        confirmed_cases = cls.get_confirmed_cases(start_date, end_date,
                                                  health_condition_id)

        context['confirmed_cases'] = confirmed_cases

        epidemics_dx = []
        non_age_cases = 0
        cases_f = 0
        cases_m = 0

        # Global Condition info
        for confirmed_case in confirmed_cases:
            # Sex distribution
            if (confirmed_case.name.gender == 'f'):
                cases_f += 1
            else:
                cases_m += 1

            # Ethnic groups distribution
            if (confirmed_case.name.name.ethnic_group):
                ethnicity = confirmed_case.name.name.ethnic_group.name
                if (ethnicity in ethnic_groups):
                    ethnic_count[ethnicity] = ethnic_count[ethnicity] + 1

            # Socioeconomic groups distribution
            if (confirmed_case.name.ses):
                ses_str = confirmed_case.name.ses_str
                ses_count[ses_str] += 1

            if not confirmed_case.name.age:
                non_age_cases += 1

        total_cases = len(confirmed_cases)

        context['confirmed_cases_num'] = total_cases
        context['cases_f'] = cases_f
        context['cases_m'] = cases_m
        context['non_age_cases'] = non_age_cases

        group_1 = group_2 = group_3 = group_4 = group_5 = 0
        group_1f = group_2f = group_3f = group_4f = group_5f = 0

        for case in confirmed_cases:

            if (case.name.age):

                # Strip to get the raw year
                age_year = parse_compute_age(case.name.age)[0]

                # Age groups in this diagnostic
                if (age_year < 5):
                    group_1 += 1
                    if (case.name.gender == 'f'):
                        group_1f += 1
                if (age_year in range(5, 14)):
                    group_2 += 1
                    if (case.name.gender == 'f'):
                        group_2f += 1
                if (age_year in range(15, 45)):
                    group_3 += 1
                    if (case.name.gender == 'f'):
                        group_3f += 1
                if (age_year in range(46, 60)):
                    group_4 += 1
                    if (case.name.gender == 'f'):
                        group_4f += 1
                if (age_year > 60):
                    group_5 += 1
                    if (case.name.gender == 'f'):
                        group_5f += 1

        cases = {'diagnosis': health_condition_id,
                 'age_group_1': group_1, 'age_group_1f': group_1f,
                 'age_group_2': group_2, 'age_group_2f': group_2f,
                 'age_group_3': group_3, 'age_group_3f': group_3f,
                 'age_group_4': group_4, 'age_group_4f': group_4f,
                 'age_group_5': group_5, 'age_group_5f': group_5f,
                 'total': total_cases, }

        # Append into the report list the resulting
        # dictionary entry

        epidemics_dx.append(cases)

        context['epidemics_dx'] = epidemics_dx

        # Configure matplotlib, for example: font.
        matplotlib_setup(mpl)

        # New cases by day
        context['cases_timeseries'] = cls.plot_cases_timeseries(
            start_date,
            end_date,
            health_condition_id, hc)

        # Cases by ethnic groups
        context['cases_ethnicity'] = cls.plot_cases_ethnicity(
            start_date,
            end_date, ethnic_count, hc)

        # Cases by Socioeconomic groups
        context['cases_ses'] = cls.plot_cases_socioeconomics(
            start_date,
            end_date, ses_count, hc)

        # Death certificates by day
        context['deaths_timeseries'] = cls.plot_deaths_timeseries(
            start_date,
            end_date,
            health_condition_id, hc)

        return context
