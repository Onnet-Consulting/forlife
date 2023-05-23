# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    invoice_info_company_name = fields.Char('Invoice Info Company Name', tracking=True)
    invoice_info_address = fields.Char('Invoice Info Address', tracking=True)
    invoice_info_tax_number = fields.Char('Invoice Info VAT', tracking=True)

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        if self.partner_id and self.config_id.store_id and not self.partner_id.store_fo_ids.filtered(lambda f: f.brand_id == self.config_id.store_id.brand_id):
            self.create_store_first_order()
        return res

    def create_store_first_order(self):
        self.env['store.first.order'].sudo().create({
            'customer_id': self.partner_id.id,
            'brand_id': self.config_id.store_id.brand_id.id,
            'store_id': self.config_id.store_id.id,
        })

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        if ui_order['to_invoice']:
            fields['invoice_info_company_name'] = ui_order.get('invoice_info_company_name')
            fields['invoice_info_address'] = ui_order.get('invoice_info_address')
            fields['invoice_info_tax_number'] = ui_order.get('invoice_info_tax_number')
        return fields
