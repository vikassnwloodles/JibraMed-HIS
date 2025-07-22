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
#                     immunization_status_report.py                     #
#########################################################################

from trytond.report import Report
from trytond.pool import Pool
from trytond.modules.health.core import parse_compute_age

__all__ = ['ImmunizationStatusReport']


class ImmunizationStatusReport(Report):
    __name__ = 'gnuhealth.immunization_status_report'

    @classmethod
    def get_context(cls, records, header, data):
        Sched = Pool().get('gnuhealth.immunization_schedule')
        Patient = Pool().get('gnuhealth.patient')
        patient = Patient(data['patient_id'])

        context = super(ImmunizationStatusReport, cls).get_context(
            records, header, data)

        context['patient'] = patient
        sched = Sched(data['immunization_schedule_id'])

        context['immunization_schedule'] = sched

        immunizations_to_check = \
            cls.get_immunizations_for_age(patient, sched)

        immunization_status = \
            cls.verify_status(immunizations_to_check)

        context['immunization_status'] = immunization_status

        return context

    @classmethod
    def get_immunizations_for_age(cls, patient, immunization_schedule):

        immunizations_for_age = []

        for vaccine in immunization_schedule.vaccines:

            for dose in vaccine.doses:
                dose_number, dose_age, age_unit, age_unit_str = dose.dose_number, \
                    dose.age_dose, dose.age_unit, dose.age_unit_str

                # Age of the person in years, months, weeks and days.
                y, m, d = parse_compute_age(patient.age)
                pdays = (y*365) + (m*365/12) + d
                pyears = pdays/365
                pmonths = pdays/(365/12)
                pweeks = pdays/7

                if ((age_unit == 'days' and pdays >= dose_age) or
                    (age_unit == 'weeks' and pweeks >= dose_age) or
                    (age_unit == 'months' and pmonths >= dose_age) or
                    (age_unit == 'years' and pyears >= dose_age)):
                    immunization_info = {
                        'patient': patient,
                        'vaccine': vaccine,
                        'dose': dose_number,
                        'dose_age': dose_age,
                        'age_unit': age_unit,
                        'age_unit_str': age_unit_str,
                        'status': None}

                    # Add to the list of this person immunization check
                    immunizations_for_age.append(immunization_info)

        return immunizations_for_age

    @classmethod
    def verify_status(cls, immunizations_to_check):
        Vaccination = Pool().get('gnuhealth.vaccination')

        result = []
        for immunization in immunizations_to_check:
            immunization['status'] = "missing"
            res = Vaccination.search_count([
                ('name', '=', immunization['patient']),
                ('dose', '=', immunization['dose']),
                ('vaccine.name', '=', immunization['vaccine'].vaccine.name),
                ])

            if res:
                immunization['status'] = 'ok'

            result.append(immunization)

        return result
