# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                      HEALTH STOCK SURGERY package                     #
#                 __init__.py: Package declaration file                 #
#########################################################################

from trytond.pool import Pool
from . import health_stock_surgery
from . import wizard


def register():
    Pool.register(
        health_stock_surgery.Move,
        health_stock_surgery.Surgery,
        wizard.wizard_create_surgery_stock_move.
        CreateSurgeryStockMoveInit,
        module='health_stock_surgery', type_='model')
    Pool.register(
        wizard.wizard_create_surgery_stock_move.
        CreateSurgeryStockMove,
        module='health_stock_surgery', type_='wizard')
