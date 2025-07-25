# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                        HEALTH PEDIATRICS package                      #
#                   health_pediatrics.py: main module                   #
#########################################################################

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from datetime import datetime
from trytond.pyson import Eval, Not, Equal
from trytond.modules.health.core import (get_health_professional,
                                         image_crop_to_ratio)

from PIL import Image


__all__ = ['Newborn', 'NeonatalApgar', 'NeonatalMedication',
           'NeonatalCongenitalDiseases', 'PediatricSymptomsChecklist']


class Newborn(ModelSQL, ModelView):
    'Newborn Information'
    __name__ = 'gnuhealth.newborn'

    STATES = {'readonly': Eval('state') == 'signed'}

    # We no longer need the legacy newborn ID, since patient.puid is
    # used. for backward compatibility reasons, we keep it.
    name = fields.Char('Newborn ID', states=STATES)
    patient = fields.Many2One(
        'gnuhealth.patient', 'Baby', required=True, states=STATES,
        help="Patient associated to this newborn")

    mother = fields.Many2One('gnuhealth.patient', 'Mother', states=STATES)
    newborn_name = fields.Char('Name at Birth', states=STATES)
    birth_date = fields.DateTime(
        'DoB', required=True,
        help="Date and Time of birth", states=STATES)
    photo = fields.Binary('Picture', states=STATES)

    # photo_crop method is used in report template, for we can not
    # find a way to keep the original aspect ratio in odt template at
    # the moment.
    @classmethod
    def photo_crop(cls, photo, ratio):
        return image_crop_to_ratio(Image, photo, ratio)

    # Sex / Gender at birth.

    sex = fields.Selection(
        [
            ('m', 'Male'),
            ('f', 'Female'),
        ], 'Sex', sort=False, required=True,
        help="Sex at birth. It might differ from the current patient"
        " gender. This is the biological sex.", states=STATES)

    sex_str = sex.translated('sex')

    state = fields.Selection([
        (None, ''),
        ('draft', 'draft'),
        ('signed', 'Signed'),
        ], 'State', readonly=True, sort=False)

    cephalic_perimeter = fields.Integer(
        'CP',
        help="Cephalic Perimeter in centimeters (cm)", states=STATES)
    length = fields.Integer(
        'Length',
        help="Length in centimeters (cm)", states=STATES)
    weight = fields.Integer(
        'Weight',
        help="Weight in grams (g)", states=STATES)

    ## Used by newborn_card report template, the page of newborn_card
    ## report is very small, so it requires compression of information.
    def get_report_length_and_weight(self):
        if self.length and self.weight:
            ## I think 'cm' and 'g' do not need to translate.
            return f'{self.length}cm, {self.weight}g'
        elif self.length:
            return f'{self.length}cm'
        elif self.weight:
            return f'{self.weight}g'
        else:
            return ''

    apgar1 = fields.Integer('APGAR 1st minute', states=STATES)
    apgar5 = fields.Integer('APGAR 5th minute', states=STATES)
    apgar_scores = fields.One2Many(
        'gnuhealth.neonatal.apgar', 'name',
        'APGAR scores', states=STATES)
    meconium = fields.Boolean('Meconium', states=STATES)

    # Deprecated. Use Patient conditions directly
    congenital_diseases = fields.One2Many(
        'gnuhealth.patient.disease',
        'newborn_id', 'Congenital diseases', states=STATES)

    reanimation_stimulation = fields.Boolean('Stimulation', states=STATES)
    reanimation_aspiration = fields.Boolean('Aspiration', states=STATES)
    reanimation_intubation = fields.Boolean('Intubation', states=STATES)
    reanimation_mask = fields.Boolean('Mask', states=STATES)
    reanimation_oxygen = fields.Boolean('Oxygen', states=STATES)
    test_vdrl = fields.Boolean('VDRL', states=STATES)
    test_toxo = fields.Boolean('Toxoplasmosis', states=STATES)
    test_chagas = fields.Boolean('Chagas', states=STATES)
    test_billirubin = fields.Boolean('Billirubin', states=STATES)
    test_audition = fields.Boolean('Audition', states=STATES)
    test_metabolic = fields.Boolean(
        'Metabolic ("heel stick screening")',
        help="Test for Fenilketonuria, Congenital Hypothyroidism, "
        "Quistic Fibrosis, Galactosemia", states=STATES)
    neonatal_ortolani = fields.Boolean('Positive Ortolani', states=STATES)
    neonatal_barlow = fields.Boolean('Positive Barlow', states=STATES)
    neonatal_hernia = fields.Boolean('Hernia', states=STATES)
    neonatal_ambiguous_genitalia = fields.Boolean(
        'Ambiguous Genitalia',
        states=STATES)
    neonatal_erbs_palsy = fields.Boolean('Erbs Palsy', states=STATES)
    neonatal_hematoma = fields.Boolean('Hematomas', states=STATES)
    neonatal_talipes_equinovarus = fields.Boolean(
        'Talipes Equinovarus',
        states=STATES)
    neonatal_polydactyly = fields.Boolean('Polydactyly', states=STATES)
    neonatal_syndactyly = fields.Boolean('Syndactyly', states=STATES)
    neonatal_moro_reflex = fields.Boolean('Moro Reflex', states=STATES)
    neonatal_grasp_reflex = fields.Boolean('Grasp Reflex', states=STATES)
    neonatal_stepping_reflex = fields.Boolean(
        'Stepping Reflex',
        states=STATES)
    neonatal_babinski_reflex = fields.Boolean(
        'Babinski Reflex',
        states=STATES)
    neonatal_blink_reflex = fields.Boolean('Blink Reflex', states=STATES)
    neonatal_sucking_reflex = fields.Boolean('Sucking Reflex', states=STATES)
    neonatal_swimming_reflex = fields.Boolean(
        'Swimming Reflex',
        states=STATES)
    neonatal_tonic_neck_reflex = fields.Boolean(
        'Tonic Neck Reflex',
        states=STATES)
    neonatal_rooting_reflex = fields.Boolean(
        'Rooting Reflex',
        states=STATES)
    neonatal_palmar_crease = fields.Boolean(
        'Transversal Palmar Crease',
        states=STATES)

    # Deprecated. Use Patient medication directly
    medication = fields.One2Many(
        'gnuhealth.patient.medication',
        'newborn_id', 'Medication')

    healthprof = fields.Many2One(
        'gnuhealth.healthprofessional',
        'Health Professional',
        help="Health professional", readonly=True)

    signed_by = fields.Many2One(
        'gnuhealth.healthprofessional', 'Signed by', readonly=True,
        states={
            'invisible': Not(Equal(Eval('state'), 'signed'))
            },
        help="Health Professional that signed this document")

    dismissed = fields.DateTime('Discharged', states=STATES)
    notes = fields.Text('Notes', states=STATES)

    # Deprecated. the following fields will be removed in 2.8
    # Decease information on fetus / newborn are linked now in
    # the obstetrics evaluation (prenatal) or patient if result of pregnancy
    # was a live birth.
    # The information is no longer shown at the view.
    # Fields to be removed : bd, died_at_delivery, died_at_the_hospital
    # died_being_transferred, tod, cod

    bd = fields.Boolean('Stillbirth')
    died_at_delivery = fields.Boolean('Died at delivery room')
    died_at_the_hospital = fields.Boolean('Died at the hospital')
    died_being_transferred = fields.Boolean(
        'Died being transferred',
        help="The baby died being transferred to another health institution")
    tod = fields.DateTime('Time of Death')
    cod = fields.Many2One('gnuhealth.pathology', 'Cause of death')

    @staticmethod
    def default_healthprof():
        return get_health_professional()

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    def __setup__(cls):
        super(Newborn, cls).__setup__()

        t = cls.__table__()
        cls._sql_constraints = [
            ('name_uniq', Unique(t, t.name),
             'The Newborn ID must be unique'),
            ('patient_uniq', Unique(t, t.patient),
             'There is already a newborn record for this patient'),
            ]
        cls._order.insert(0, ('birth_date', 'DESC'))

        cls._buttons.update({
            'sign_newborn': {'invisible': Equal(Eval('state'), 'signed')}
            })

    @classmethod
    @ModelView.button
    def sign_newborn(cls, newborns):
        signing_hp = get_health_professional()

        cls.write(newborns, {
            'state': 'signed',
            'signed_by': signing_hp,
            })

    @classmethod
    def write(cls, newborns, values):
        pool = Pool()
        Patient = pool.get('gnuhealth.patient')
        Party = pool.get('party.party')

        party = []
        patient = []

        for newborn in newborns:

            newborn_patient_id = newborn.patient.id

            person = Patient.browse([newborn_patient_id])[0].name
            pat = Patient.browse([newborn_patient_id])[0]

            # Update the birth date on the party model upon WRITING it on the
            # newborn model

            born_date = datetime.date(newborn.birth_date)

            party.append(person)

            Party.write(party, {'dob': born_date})

            # Update the biological sex on the patient model upon WRITING
            # it on the newborn model

            if values.get('sex'):
                biological_sex = values.get('sex')

                patient.append(pat)

                Patient.write(patient, {'biological_sex': biological_sex})

        return super(Newborn, cls).write(newborns, values)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        vlist = [x.copy() for x in vlist]
        Patient = pool.get('gnuhealth.patient')
        Party = pool.get('party.party')

        party = []
        patient = []

        for values in vlist:
            newborn_patient_id = values['patient']

            person = Patient.browse([newborn_patient_id])[0].name
            pat = Patient.browse([newborn_patient_id])[0]

            # Update the birth date on the party model upon CREATING it on the
            # newborn model

            born_date = datetime.date(values['birth_date'])

            party.append(person)

            Party.write(party, {'dob': born_date})

            # Update the biological sex on the patient model upon CREATING
            # it on the newborn model

            if values.get('sex'):
                biological_sex = values.get('sex')

                patient.append(pat)

                Patient.write(patient, {'biological_sex': biological_sex})

        return super(Newborn, cls).create(vlist)

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op, ('name',) + tuple(clause[1:]),
                ('patient',) + tuple(clause[1:]),
                ]


class NeonatalApgar(ModelSQL, ModelView):
    'Neonatal APGAR Score'
    __name__ = 'gnuhealth.neonatal.apgar'

    name = fields.Many2One('gnuhealth.newborn', 'Newborn')

    apgar_minute = fields.Integer('Minute', required=True)

    apgar_appearance = fields.Selection([
        ('0', 'central cyanosis'),
        ('1', 'acrocyanosis'),
        ('2', 'no cyanosis'),
        ], 'Appearance', required=True)

    apgar_pulse = fields.Selection([
        ('0', 'Absent'),
        ('1', '< 100'),
        ('2', '> 100'),
        ], 'Pulse', required=True)

    apgar_grimace = fields.Selection([
        ('0', 'No response to stimulation'),
        ('1', 'grimace when stimulated'),
        ('2', 'cry or pull away when stimulated'),
        ], 'Grimace', required=True, sort=False)

    apgar_activity = fields.Selection([
        ('0', 'None'),
        ('1', 'Some flexion'),
        ('2', 'flexed arms and legs'),
        ], 'Activity', required=True, sort=False)

    apgar_respiration = fields.Selection([
        ('0', 'Absent'),
        ('1', 'Weak / Irregular'),
        ('2', 'strong'),
        ], 'Respiration', required=True, sort=False)

    apgar_score = fields.Integer('APGAR Score')

    @fields.depends(
        'apgar_respiration', 'apgar_activity', 'apgar_grimace',
        'apgar_pulse', 'apgar_appearance')
    def on_change_with_apgar_score(self):
        apgar_appearance = self.apgar_appearance or '0'
        apgar_pulse = self.apgar_pulse or '0'
        apgar_grimace = self.apgar_grimace or '0'
        apgar_activity = self.apgar_activity or '0'
        apgar_respiration = self.apgar_respiration or '0'

        apgar_score = int(apgar_appearance) + int(apgar_pulse) + \
            int(apgar_grimace) + int(apgar_activity) + int(apgar_respiration)

        return apgar_score


# Deprecated in 3.0 - Use the main patient form
class NeonatalMedication(metaclass=PoolMeta):
    __name__ = 'gnuhealth.patient.medication'

    newborn_id = fields.Many2One('gnuhealth.newborn', 'Newborn')


# Deprecated in 3.0  - Use main patient form
class NeonatalCongenitalDiseases(metaclass=PoolMeta):
    __name__ = 'gnuhealth.patient.disease'

    newborn_id = fields.Many2One('gnuhealth.newborn', 'Newborn')


class PediatricSymptomsChecklist(ModelSQL, ModelView):
    'Pediatric Symptoms Checklist'
    __name__ = 'gnuhealth.patient.psc'

    patient = fields.Many2One('gnuhealth.patient', 'Patient', required=True)

    evaluation_date = fields.Many2One(
        'gnuhealth.appointment', 'Appointment',
        help="Enter or select the date / ID of the appointment related to "
        "this evaluation")

    evaluation_start = fields.DateTime('Date', required=True)

    user_id = fields.Many2One('res.user', 'Health Professional', readonly=True)

    notes = fields.Text('Notes')

    psc_aches_pains = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Complains of aches and pains', sort=False)

    psc_spend_time_alone = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Spends more time alone', sort=False)

    psc_tires_easily = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Tires easily, has little energy', sort=False)

    psc_fidgety = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Fidgety, unable to sit still', sort=False)

    psc_trouble_with_teacher = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Has trouble with teacher', sort=False)

    psc_less_interest_in_school = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Less interested in school', sort=False)

    psc_acts_as_driven_by_motor = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Acts as if driven by a motor', sort=False)

    psc_daydreams_too_much = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Daydreams too much', sort=False)

    psc_distracted_easily = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Distracted easily', sort=False)

    psc_afraid_of_new_situations = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Is afraid of new situations', sort=False)

    psc_sad_unhappy = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Feels sad, unhappy', sort=False)

    psc_irritable_angry = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Is irritable, angry', sort=False)

    psc_feels_hopeless = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Feels hopeless', sort=False)

    psc_trouble_concentrating = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Has trouble concentrating', sort=False)

    psc_less_interested_in_friends = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Less interested in friends', sort=False)

    psc_fights_with_others = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Fights with other children', sort=False)

    psc_absent_from_school = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Absent from school', sort=False)

    psc_school_grades_dropping = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'School grades dropping', sort=False)

    psc_down_on_self = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Is down on him or herself', sort=False)

    psc_visit_doctor_finds_ok = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Visits the doctor with doctor finding nothing wrong', sort=False)

    psc_trouble_sleeping = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Has trouble sleeping', sort=False)

    psc_worries_a_lot = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Worries a lot', sort=False)

    psc_wants_to_be_with_parents = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Wants to be with you more than before', sort=False)

    psc_feels_is_bad_child = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Feels he or she is bad', sort=False)

    psc_takes_unnecesary_risks = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Takes unnecessary risks', sort=False)

    psc_gets_hurt_often = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Gets hurt frequently', sort=False)

    psc_having_less_fun = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Seems to be having less fun', sort=False)

    psc_act_as_younger = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Acts younger than children his or her age', sort=False)

    psc_does_not_listen_to_rules = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Does not listen to rules', sort=False)

    psc_does_not_show_feelings = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Does not show feelings', sort=False)

    psc_does_not_get_people_feelings = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Does not get people feelings', sort=False)

    psc_teases_others = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Teases others', sort=False)

    psc_blames_others = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Blames others for his or her troubles', sort=False)

    psc_takes_things_from_others = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Takes things that do not belong to him or her', sort=False)

    psc_refuses_to_share = fields.Selection([
        (None, ''),
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
        ], 'Refuses to share', sort=False)

    psc_total = fields.Integer('PSC Total')

    @staticmethod
    def default_user_id():
        User = Pool().get('res.user')
        user = User(Transaction().user)
        return int(user.id)

    @staticmethod
    def default_psc_total():
        return 0

    @fields.depends(
        'psc_aches_pains', 'psc_spend_time_alone',
        'psc_tires_easily', 'psc_fidgety', 'psc_trouble_with_teacher',
        'psc_less_interest_in_school', 'psc_acts_as_driven_by_motor',
        'psc_daydreams_too_much', 'psc_distracted_easily',
        'psc_afraid_of_new_situations', 'psc_sad_unhappy',
        'psc_irritable_angry', 'psc_feels_hopeless',
        'psc_trouble_concentrating', 'psc_less_interested_in_friends',
        'psc_fights_with_others', 'psc_absent_from_school',
        'psc_school_grades_dropping', 'psc_down_on_self',
        'psc_visit_doctor_finds_ok', 'psc_trouble_sleeping',
        'psc_worries_a_lot', 'psc_wants_to_be_with_parents',
        'psc_feels_is_bad_child', 'psc_takes_unnecesary_risks',
        'psc_gets_hurt_often', 'psc_having_less_fun',
        'psc_act_as_younger', 'psc_does_not_listen_to_rules',
        'psc_does_not_show_feelings',
        'psc_does_not_get_people_feelings',
        'psc_teases_others', 'psc_takes_things_from_others',
        'psc_refuses_to_share')
    def on_change_with_psc_total(self):

        psc_aches_pains = self.psc_aches_pains or '0'
        psc_spend_time_alone = self.psc_spend_time_alone or '0'
        psc_tires_easily = self.psc_tires_easily or '0'
        psc_fidgety = self.psc_fidgety or '0'
        psc_trouble_with_teacher = self.psc_trouble_with_teacher or '0'
        psc_less_interest_in_school = self.psc_less_interest_in_school or '0'
        psc_acts_as_driven_by_motor = self.psc_acts_as_driven_by_motor or '0'
        psc_daydreams_too_much = self.psc_daydreams_too_much or '0'
        psc_distracted_easily = self.psc_distracted_easily or '0'
        psc_afraid_of_new_situations = self.psc_afraid_of_new_situations or '0'
        psc_sad_unhappy = self.psc_sad_unhappy or '0'
        psc_irritable_angry = self.psc_irritable_angry or '0'
        psc_feels_hopeless = self.psc_feels_hopeless or '0'
        psc_trouble_concentrating = self.psc_trouble_concentrating or '0'
        psc_less_interested_in_friends = \
            self.psc_less_interested_in_friends or '0'
        psc_fights_with_others = self.psc_fights_with_others or '0'
        psc_absent_from_school = self.psc_absent_from_school or '0'
        psc_school_grades_dropping = self.psc_school_grades_dropping or '0'
        psc_down_on_self = self.psc_down_on_self or '0'
        psc_visit_doctor_finds_ok = self.psc_visit_doctor_finds_ok or '0'
        psc_trouble_sleeping = self.psc_trouble_sleeping or '0'
        psc_worries_a_lot = self.psc_worries_a_lot or '0'
        psc_wants_to_be_with_parents = self.psc_wants_to_be_with_parents or '0'
        psc_feels_is_bad_child = self.psc_feels_is_bad_child or '0'
        psc_takes_unnecesary_risks = self.psc_takes_unnecesary_risks or '0'
        psc_gets_hurt_often = self.psc_gets_hurt_often or '0'
        psc_having_less_fun = self.psc_having_less_fun or '0'
        psc_act_as_younger = self.psc_act_as_younger or '0'
        psc_does_not_listen_to_rules = self.psc_does_not_listen_to_rules or '0'
        psc_does_not_show_feelings = self.psc_does_not_show_feelings or '0'
        psc_does_not_get_people_feelings = \
            self.psc_does_not_get_people_feelings or '0'
        psc_teases_others = self.psc_teases_others or '0'
        psc_takes_things_from_others = self.psc_takes_things_from_others or '0'
        psc_refuses_to_share = self.psc_refuses_to_share or '0'

        psc_total = int(psc_aches_pains) + int(psc_spend_time_alone) + \
            int(psc_tires_easily) + int(psc_fidgety) + \
            int(psc_trouble_with_teacher) + \
            int(psc_less_interest_in_school) + \
            int(psc_acts_as_driven_by_motor) + \
            int(psc_daydreams_too_much) + int(psc_distracted_easily) + \
            int(psc_afraid_of_new_situations) + int(psc_sad_unhappy) + \
            int(psc_irritable_angry) + int(psc_feels_hopeless) + \
            int(psc_trouble_concentrating) + \
            int(psc_less_interested_in_friends) + \
            int(psc_fights_with_others) + int(psc_absent_from_school) + \
            int(psc_school_grades_dropping) + int(psc_down_on_self) + \
            int(psc_visit_doctor_finds_ok) + int(psc_trouble_sleeping) + \
            int(psc_worries_a_lot) + int(psc_wants_to_be_with_parents) + \
            int(psc_feels_is_bad_child) + int(psc_takes_unnecesary_risks) + \
            int(psc_gets_hurt_often) + int(psc_having_less_fun) + \
            int(psc_act_as_younger) + int(psc_does_not_listen_to_rules) + \
            int(psc_does_not_show_feelings) + \
            int(psc_does_not_get_people_feelings) + \
            int(psc_teases_others) + \
            int(psc_takes_things_from_others) + \
            int(psc_refuses_to_share)

        return psc_total
