from odoo import models, _
from odoo.exceptions import ValidationError


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        res = super(InheritStockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.inventory_id:
            res.update({
                'date': self.inventory_id.date.date(),
                'invoice_date_due': self.inventory_id.date.date(),
            })
        return res
