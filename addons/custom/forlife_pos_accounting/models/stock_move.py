from odoo import models, _, fields
from odoo.exceptions import ValidationError


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    pos_order_line_id = fields.Many2one('pos.order.line', readonly=True)

    def _prepare_account_move_vals(
            self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
    ):
        if self.pos_order_line_id:
            if (not self.pos_order_line_id.with_purchase_condition and self.pos_order_line_id.is_reward_line
                    and self.pos_order_line_id.product_id.id == self.product_id.id):
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
