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
