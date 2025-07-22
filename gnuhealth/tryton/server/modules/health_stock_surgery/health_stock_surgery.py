# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2013 Sebastian Marro <smarro@thymbra.com>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                  HEALTH STOCK SURGERY package                         #
#              health_stock_surgery.py: main module                     #
#########################################################################

from trytond.model import fields

from trytond.pool import PoolMeta

__all__ = ['Move', 'Surgery']


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def _get_origin(cls):
        return super(Move, cls)._get_origin() + [
            'gnuhealth.surgery',
            ]


class Surgery(metaclass=PoolMeta):
    __name__ = 'gnuhealth.surgery'

    moves = fields.One2Many('stock.move', 'origin', 'Moves', readonly=True)
    location = fields.Many2One(
        'stock.location',
        'Stock Location', domain=[('type', '=', 'storage')])
