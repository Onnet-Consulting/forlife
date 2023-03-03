from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_view_voucher(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_voucher.forlife_voucher_action')
        action['domain'] = [('sale_id', '=', self.id)]
        return action
