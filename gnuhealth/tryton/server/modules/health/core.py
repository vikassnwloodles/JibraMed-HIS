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
#               core.py: commonly used ojects and methods               #
#########################################################################

import pytz

from dateutil.relativedelta import relativedelta
from datetime import datetime
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.i18n import gettext

from .exceptions import (NoAssociatedHealthProfessional)

import os
import io
import json

def convert_date_timezone(sdate, target):
    """
    Convert dates from UTC to local timezone and viceversa
    Datetime values are stored in UTC, so we need conversion
    """

    Company = Pool().get('company.company')

    institution_timezone = None
    company_id = Transaction().context.get('company')
    if company_id:
        company = Company(company_id)
        if company.timezone:
            institution_timezone = pytz.timezone(company.timezone)

    if (target == 'utc'):
        # Convert date to UTC timezone
        res = institution_timezone.localize(sdate).astimezone(pytz.utc)
    else:
        # Convert from UTC to institution local timezone
        res = pytz.utc.localize(sdate).astimezone(institution_timezone)
    return res


def estimated_date_from_years(years_old):
    """ returns a date of substracting the
        referred number of years from today's date
        It can be used in different context, such as to estimate
        the date of birth from a referred age in years
    """

    today = datetime.today().date()
    est_dob = today - relativedelta(years=years_old)
    return est_dob


def compute_age_from_dates(dob, deceased, dod, gender, caller, extra_date):
    """ Get the person's age.

    Calculate the current age of the patient or age at time of death.

    Returns:
    If caller == 'age': str in Y-M-D,
       caller == 'childbearing_age': boolean,
       caller == 'raw_age': [Y, M, D]

    """
    today = datetime.today().date()

    if dob:
        start = datetime.strptime(str(dob), '%Y-%m-%d')
        end = datetime.strptime(str(today), '%Y-%m-%d')

        if extra_date:
            end = datetime.strptime(str(extra_date), '%Y-%m-%d')

        if deceased and dod:
            end = datetime.strptime(
                        str(dod), '%Y-%m-%d %H:%M:%S')

        rdelta = relativedelta(end, start)

        years_months_days = format_years_months_days(
            years=rdelta.years,
            months=rdelta.months,
            days=rdelta.days)
    else:
        return None

    if caller == 'age':
        return years_months_days

    elif caller == 'childbearing_age':
        if (rdelta.years >= 11
           and rdelta.years <= 55 and gender == 'f'):
            return True
        else:
            return False

    elif caller == 'raw_age':
        return [rdelta.years, rdelta.months, rdelta.days]

    else:
        return None


def format_years_months_days(years=None, months=None, days=None):
    year_str = gettext('health.msg_compute_age_from_dates_year_str')
    month_str = gettext('health.msg_compute_age_from_dates_month_str')
    day_str = gettext('health.msg_compute_age_from_dates_day_str')

    ymd_format = '{years}{sep}{year_str}{sep}' \
                 '{months}{sep}{month_str}{sep}' \
                 '{days}{sep}{day_str}{sep}'

    return ymd_format.format(
        sep='\u200b',  # Zero width space
        # Make sure output.split(sep)[0, 2, 4] = [years, months, days], 
        # and we use '\u200d' (zero width joiner) as placeholder.
        years=isinstance(years, int) and str(years) or '\u200d',
        year_str=isinstance(years, int) and year_str or '\u200d',
        months=isinstance(months, int) and str(months) or '\u200d',
        month_str=isinstance(months, int) and month_str or '\u200d',
        days=isinstance(days, int) and str(days) or '\u200d',
        day_str=isinstance(days, int) and day_str or '\u200d')


def parse_compute_age(age):
    """ Parse age returned by compute_age_from_dates function."""
    if isinstance(age, str):
        return parse_compute_age_str(age)
    else:
        return age


def parse_compute_age_str(age_str):
    """ Parse age string returned by compute_age_from_dates function"""
    age_str = age_str.strip()
    sep = '\u200b'  # Zero width space
    if age_str.endswith(sep):
        return parse_compute_age_str_with_zero_width_space(age_str)
    else:
        return parse_compute_age_str_with_one_char_string(age_str)


def parse_compute_age_str_with_zero_width_space(age_str):
    """Parse age string seperate with zero width space.

    '10y 2m 03d' => [10, 2, 3]

    'y', 'm', 'd' can be translated to other languages, and this three
    string are surrounded with zero width space: '\u200b'.

    """
    sep = '\u200b'  # Zero width space
    age = age_str.split(sep)
    try:
        years = int(age[0])
    except:
        years = None
    try:
        months = int(age[2])
    except:
        months = None
    try:
        days = int(age[4])
    except:
        days = None
    return [years, months, days]


def parse_compute_age_str_with_one_char_string(age_str):
    """ Parse age string which is like: '10y 2m 03d'.

    'y', 'm', 'd' are 1 char strings, which can be translated to other
    languages.

    For example:

    '10y 2m 03d' => [10, 2, 3]

    Note: Previously, compute_age_from_dates will return '10y 4m 4d'
    style age string, so this function was retained for compatibility.
    """
    try:
        year = int(age_str.split(' ')[0][:-1])
        month = int(age_str.split(' ')[1][:-1])
        day = int(age_str.split(' ')[2][:-1])
        return [year, month, day]
    except:
        return [None, None, None]


def get_institution():
    # Retrieve the institution associated to this GNU Health instance
    # That is associated to the Company.
    pool = Pool()
    Company = pool.get('company.company')
    Institution = pool.get('gnuhealth.institution')
    company = Company.__table__()
    institution = Institution.__table__()

    company_id = Transaction().context.get('company')

    cursor = Transaction().connection.cursor()
    cursor.execute(*company.join(institution, condition=(
                institution.name == company.party)).select(
            institution.id,
            where=(company.id == company_id)))
    institution_id = cursor.fetchone()
    if institution_id:
        return int(institution_id[0])


def get_health_professional(required=True):
    # Get the professional associated to the internal user id
    # that logs into GNU Health
    # If the method is called with the arg "required" as False, then
    # the error message won't be shown in the case of not finding
    # the corresponding healthprof (eg, creating a new appointment)
    pool = Pool()
    Party = pool.get('party.party')
    Professional = pool.get('gnuhealth.healthprofessional')
    party = Party.__table__()
    professional = Professional.__table__()

    cursor = Transaction().connection.cursor()
    cursor.execute(
        *party.join(professional,
                    condition=(professional.name == party.id)).select(
            professional.id,
            where=(
                (party.is_healthprof)
                & (party.internal_user == Transaction().user))))
    healthprof_id = cursor.fetchone()
    if healthprof_id:
        return int(healthprof_id[0])
    else:
        if required and not pool.test:
            raise NoAssociatedHealthProfessional(gettext(
                ('health.msg_no_associated_health_professional'))
            )

def image_crop_to_ratio(plt, image, ratio):
    """ Center-crop an image, make it conform to the ratio,
    This function is useful to adjust ID card photo.
    """
    img = plt.open(io.BytesIO(image))
    orig_width, orig_height = img.size
    orig_ratio = float(orig_height / orig_width)

    if orig_ratio >= ratio:
        width = orig_width
        height = int(width * ratio)
        x = 0
        y = (orig_height - height) / 2
    else:
        height = orig_height
        width = int(height / ratio)
        x = (orig_width - width) / 2
        y = 0
        
    regin = (x, y, width + x, height + y)

    new_img = img.crop(regin)

    # Make a PNG image from PIL without the need to create a temp
    # file.
    holder = io.BytesIO()
    new_img.save(holder, format='png')
    new_img_png = holder.getvalue()
    holder.close()

    return bytearray(new_img_png)


# Matplotlib will be used by many report.py in the future, so we add a
# setup function to here.
def matplotlib_setup(matplotlab):
    matplotlibrc = os.path.join(matplotlab.get_configdir(), 'matplotlibrc')
    if os.path.exists(matplotlibrc):
        print(f'Matplotlib: RC file: {matplotlibrc} is found, just use it.')
    else:
        rc_conf_json = gettext('health.msg_matplotlib_rc_config_json_str')
        rc_conf = json.loads(rc_conf_json)
        rc_conf.pop('@comment', None)
        matplotlab.rcParams.update(rc_conf)
        print(f'Matplotlib: Use rcParams: {rc_conf}.')
