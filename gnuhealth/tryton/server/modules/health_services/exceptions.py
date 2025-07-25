# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# This file is part of GNU Health.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.exceptions import UserError, UserWarning
from trytond.model.exceptions import ValidationError


class ServiceAlreadyInvoiced(ValidationError):
    pass

class NoServiceAssociated(UserError):
    pass

class ServiceHasBeenUpdated(UserError):
    pass

class NoProductAssociated(UserError):
    pass

class NoInvoiceAddress(UserError):
    pass

class NoPaymentTerm(UserError):
    pass

class NoAccountReceivable(UserError):
    pass
