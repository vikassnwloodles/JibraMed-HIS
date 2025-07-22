# Copyright (C) 2008-2024 Luis Falcon <lfalcon@gnusolidario.org>
# Copyright (C) 2011-2024 GNU Solidario <health@gnusolidario.org>
# Copyright (C) 2013  Sebastian Marro <smarro@gnusolidario.org>
# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
# SPDX-FileCopyrightText: 2013 Sebastian Marro <smarro@thymbra.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from trytond.wizard import Wizard, StateView, Button, StateTransition
from trytond.model import ModelView
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.i18n import gettext
from ..exceptions import StockMoveExists

__all__ = ['CreateSurgeryStockMoveInit', 'CreateSurgeryStockMove']


class CreateSurgeryStockMoveInit(ModelView):
    'Create Surgery Stock Move Init'
    __name__ = 'gnuhealth.surgery.stock.move.init'


class CreateSurgeryStockMove(Wizard):
    'Create Surgery Stock Move'
    __name__ = 'gnuhealth.surgery.stock.move.create'

    start = StateView(
        'gnuhealth.surgery.stock.move.init',
        'health_stock_surgery.view_create_surgery_stock_move', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button(
                'Create Stock Move', 'create_stock_move',
                'tryton-ok', True),
        ])
    create_stock_move = StateTransition()

    def transition_create_stock_move(self):
        pool = Pool()
        StockMove = pool.get('stock.move')
        Surgery = pool.get('gnuhealth.surgery')

        moves = []
        surgeries = Surgery.browse(Transaction().context.get(
            'active_ids'))
        for surgery in surgeries:

            if surgery.moves:
                raise StockMoveExists(
                    gettext('health_stock_surgery.msg_stock_move_exists')
                    )

            from_location = surgery.location
            if from_location.type == 'warehouse':
                from_location = from_location.storage_location
            to_location = surgery.patient.name.customer_location

            for line in surgery.supplies:
                move = StockMove()
                move.origin = surgery
                move.from_location = from_location
                move.to_location = to_location
                move.product = line.supply
                move.unit_price = line.supply.list_price
                move.cost_price = line.supply.cost_price

                # Use the actual amount of supply quantity used
                move.quantity = int(line.qty_used)
                move.uom = line.supply.default_uom
                moves.append(move)
        StockMove.save(moves)
        StockMove.do(moves)
        return 'end'
