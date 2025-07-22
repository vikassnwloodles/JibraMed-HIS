# SPDX-FileCopyrightText: 2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from trytond.pool import PoolMeta


class Cron(metaclass=PoolMeta):
    # Include the Server synchronization on the scheduler
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
            ('gnuhealth.orthanc.config|sync', "Orthanc: Sync studies"),
            ])
