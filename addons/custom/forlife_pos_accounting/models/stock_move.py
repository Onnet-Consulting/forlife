from odoo import models


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(
            self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
    ):
        if self.picking_id.pos_order_id and self.product_id.check_is_promotion():
            if self._is_out():
                credit_account_id = self.product_id.get_product_gift_account()

        return super(InheritStockMove, self)._prepare_account_move_vals(
            credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
        )
