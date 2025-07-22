# SPDX-FileCopyrightText: 2019-2022 Chris Zimmerman <chris@teffalump.com>
# SPDX-FileCopyrightText: 2021-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2021-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                       HEALTH ORTHANC package                          #
#                  __init__.py: Package declaration file                #
#########################################################################

"""
Initialization module for the ``health_orthanc`` module.

This module registers the necessary classes and methods of the
``health_orthanc`` module and its wizard in the Tryton pool.
This allows other modules to access the functionalities provided by
the ``health_orthanc`` module.
"""

from trytond.pool import Pool
from . import health_orthanc
from . import wizard
from . import ir


def register():
    Pool.register(
        wizard.wizard.AddOrthancInit,
        wizard.wizard.AddOrthancResult,
        health_orthanc.OrthancServerConfig,
        health_orthanc.OrthancWorklistTemplate,
        health_orthanc.OrthancStudy,
        health_orthanc.OrthancPatient,
        health_orthanc.ImagingTestRequest,
        health_orthanc.ImagingTest,
        health_orthanc.TestResult,
        health_orthanc.Patient,
        ir.Cron,
        module="health_orthanc",
        type_="model",
    )
    Pool.register(
        wizard.wizard.FullSyncOrthanc, module="health_orthanc", type_="wizard")
