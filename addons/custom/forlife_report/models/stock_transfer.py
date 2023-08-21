from odoo import api, fields, models


class StockTransfer(models.Model):
    _inherit = 'stock.transfer'

    def open_popup_print_stock_transfer(self):
        action = self.env["ir.actions.actions"]._for_xml_id("forlife_report.popup_print_stock_transfer_action")
        action['res_id'] = self.id
        action['context'] = self._context
        return action
