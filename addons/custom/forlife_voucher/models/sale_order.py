from odoo import api, fields, models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_view_voucher(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_voucher.forlife_voucher_action')
        action['domain'] = [('sale_id', '=', self.id)]
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped, final, date)
        for order in self:
            invoice_line_vals = []
            for line in order.order_line:
                if not line.product_id.program_voucher_id or line.product_id.program_voucher_id.purpose_id.ref != 'B' or line.price_unit == line.product_id.price:
                    continue
                if line.product_id.price - line.price_unit <= 0:
                    continue
                if not line.product_id.categ_id.property_price_account_id:
                    continue
                invoice_line_vals.append((0, 0, {
                    # 'display_type': line.display_type or 'line_section',
                    'sequence': line.sequence,
                    'account_id': line.product_id.categ_id.property_price_account_id.id,
                    'quantity': line.qty_delivered,
                    # 'sale_line_ids': [Command.link(line.id)],
                    'price_unit': line.product_id.price - line.price_unit,
                    'is_downpayment': line.is_downpayment,
                }))
            if invoice_line_vals:
                res.invoice_line_ids = invoice_line_vals
        return res
