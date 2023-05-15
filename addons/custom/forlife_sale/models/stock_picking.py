from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def confirm_from_so(self, condition=None):
        if condition:
            self._sanity_check()
            self.move_ids._set_quantities_to_reservation()
            self.with_context(skip_immediate=True).button_validate()
        else:
            self.action_confirm()

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if vals.get('note'):
            account_id = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
            account_id.update({'narration': self.note})
        return res
