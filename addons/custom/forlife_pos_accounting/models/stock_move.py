from odoo import models, _
from odoo.exceptions import ValidationError


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(
            self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
    ):
        context = self._context
        if context.get('pos_order_id'):
            if self.env['pos.order.line'].sudo().search([
                ('order_id', '=', context['pos_order_id']),
                ('product_id', '=', self.product_id.id),
                ('with_purchase_condition', '!=', True),
                ('is_reward_line', '=', True)
            ]):
                gift_account = self.product_id.get_product_gift_account()
                if not gift_account:
                    raise ValidationError(_(
                        'Product categories "%s" has not configured gift account!',
                        self.product_id.product_tmpl_id.categ_id.display_name
                    ))
                if self._is_out():
                    debit_account_id = gift_account.id
                elif self._is_in():
                    credit_account_id = gift_account.id
        return super(InheritStockMove, self)._prepare_account_move_vals(
            credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
        )
