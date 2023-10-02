from odoo.tools import frozendict
from odoo import _
from . import res_company
from . import res_config_settings
from . import journal
from . import product
from . import point_promotion
from . import promotion_program
from . import member_card
from . import pos_order
from . import account_move
from . import stock_move
from . import pos_session
from . import pos_payment
from . import stock_picking

from odoo.addons.account.models.account_move_line import AccountMoveLine as AccountMoveLineInherit


# Monkey Patch for method _compute_tax_key and _compute_all_tax with base Odoo code in last version
# TODO: Xóa code dưới đây sau khi cập nhật addons base Odoo version mới
def _compute_tax_key(self):
    for line in self:
        if line.tax_repartition_line_id:
            line.tax_key = frozendict({
                'tax_repartition_line_id': line.tax_repartition_line_id.id,
                'group_tax_id': line.group_tax_id.id,
                'account_id': line.account_id.id,
                'currency_id': line.currency_id.id,
                'analytic_distribution': line.analytic_distribution,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
                'partner_id': line.partner_id.id,
                'move_id': line.move_id.id,
                'display_type': 'epd' if line.name and _('(Discount)') in line.name else line.display_type,
            })
        else:
            line.tax_key = frozendict({'id': line.id})


def _compute_all_tax(self):
    for line in self:
        sign = line.move_id.direction_sign
        if line.display_type == 'tax':
            line.compute_all_tax = {}
            line.compute_all_tax_dirty = False
            continue
        if line.display_type == 'product' and line.move_id.is_invoice(True):
            amount_currency = sign * line.price_unit * (1 - line.discount / 100)
            handle_price_include = True
            quantity = line.quantity
        else:
            amount_currency = line.amount_currency
            handle_price_include = False
            quantity = 1
        compute_all_currency = line.tax_ids.compute_all(
            amount_currency,
            currency=line.currency_id,
            quantity=quantity,
            product=line.product_id,
            partner=line.move_id.partner_id or line.partner_id,
            is_refund=line.is_refund,
            handle_price_include=handle_price_include,
            include_caba_tags=line.move_id.always_tax_exigible,
            fixed_multiplicator=sign,
        )
        rate = line.amount_currency / line.balance if line.balance else 1
        line.compute_all_tax_dirty = True
        line.compute_all_tax = {
            frozendict({
                'tax_repartition_line_id': tax['tax_repartition_line_id'],
                'group_tax_id': tax['group'] and tax['group'].id or False,
                'account_id': tax['account_id'] or line.account_id.id,
                'currency_id': line.currency_id.id,
                'analytic_distribution': (tax['analytic'] or not tax['use_in_tax_closing']) and line.analytic_distribution,
                'tax_ids': [(6, 0, tax['tax_ids'])],
                'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                'move_id': line.move_id.id,
                'display_type': line.display_type,
            }): {
                'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
                'balance': tax['amount'] / rate,
                'amount_currency': tax['amount'],
                'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
            }
            for tax in compute_all_currency['taxes']
            if tax['amount']
        }
        if not line.tax_repartition_line_id:
            line.compute_all_tax[frozendict({'id': line.id})] = {
                'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
            }

AccountMoveLineInherit._compute_tax_key = _compute_tax_key
AccountMoveLineInherit._compute_all_tax = _compute_all_tax
