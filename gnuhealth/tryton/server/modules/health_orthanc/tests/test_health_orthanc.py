# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                       HEALTH ORTHANC package                          #
#                test_health.py health unittest file                    #
#########################################################################
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class HealthTestOrthancCase(ModuleTestCase):
    '''
    Test Health module.
    '''
    module = 'health_orthanc'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        HealthTestOrthancCase))
    return suite
