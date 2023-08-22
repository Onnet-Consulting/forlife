from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def open_popup_print_stock_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("forlife_report.popup_print_stock_picking_action")
        action['res_id'] = self.id
        action['context'] = self._context
        return action
