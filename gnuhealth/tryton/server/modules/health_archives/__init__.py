# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                           HEALTH ARCHIVE package                      #
#                __init__.py: Package declaration file                  #
#########################################################################

from trytond.pool import Pool
from . import health_archives


def register():
    Pool.register(
        health_archives.PaperArchive,
        module='health_archives', type_='model')
