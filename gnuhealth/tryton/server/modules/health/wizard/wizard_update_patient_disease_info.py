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
#              wizard_update_patient_disease_info.py: wizard            #
#########################################################################
from trytond.wizard import Wizard, StateView, Button, StateAction, StateTransition
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool

from trytond.modules.health.core import (parse_compute_age)
from trytond.i18n import gettext

from ..exceptions import (PatientDiseaseAlreadyExists)

__all__ = ['UpdatePatientDiseaseInfo']


class UpdatePatientDiseaseInfo(Wizard):
    __name__ = 'gnuhealth.update_patient_disease_info'

    start = StateTransition()

    update_disease = StateView(
        'gnuhealth.patient.disease',
        'health.gnuhealth_patient_diseases_view_form_for_wizard', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Save', 'save', 'tryton-ok', default=True)])

    save = StateTransition()

    def transition_start(self):
        pool = Pool()
        Disease = Pool().get('gnuhealth.patient.disease')
        Evaluation = pool.get('gnuhealth.patient.evaluation')

        evaluation = Evaluation.browse(
            [Transaction().context.get('active_id')])[0]

        existing_disease = Disease.search(
            [('name', '=', evaluation.patient),
             ('pathology', '=', evaluation.diagnosis),
             ('diagnosed_date', '=', evaluation.evaluation_endtime.date())])

        if existing_disease:
            raise PatientDiseaseAlreadyExists(
                gettext('health.msg_patient_disease_already_exists')
            )
            return 'end'
        else:
            return 'update_disease'

    def default_update_disease(self, fields):
        pool = Pool()
        Evaluation = pool.get('gnuhealth.patient.evaluation')

        evaluation = Evaluation.browse(
            [Transaction().context.get('active_id')])[0]

        return {'name': evaluation.patient and evaluation.patient.id,
                'age': evaluation.patient and parse_compute_age(evaluation.patient.age)[0],
                'age_str': evaluation.patient and evaluation.patient.age,
                'pathology': evaluation.diagnosis and evaluation.diagnosis.id,
                'institution': evaluation.institution and evaluation.institution.id,
                'diagnosed_date': evaluation.evaluation_endtime}

    def transition_save(self):
        pool = Pool()
        Disease = Pool().get('gnuhealth.patient.disease')
        Disease.save([self.update_disease])
        return 'end'
