from odoo import models


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(
            self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
    ):
        if self._context.get('pos_order_id'):
            gift_account = self.product_id.get_product_gift_account()
            if gift_account:
                if self._is_out():
                    credit_account_id = gift_account.id

        return super(InheritStockMove, self)._prepare_account_move_vals(
            credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
        )
