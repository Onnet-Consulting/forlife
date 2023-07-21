from odoo import models, _
from datetime import datetime, timedelta

class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        res = super(InheritStockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.inventory_id:
            invoice_date = (self.inventory_id.date + timedelta(hours=7)).date()
            res.update({
                'date': invoice_date,
                'invoice_date_due': invoice_date,
            })
        return res
