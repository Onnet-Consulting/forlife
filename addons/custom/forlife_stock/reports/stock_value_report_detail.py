# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools


class StockValueReportDetail(models.TransientModel):
    _name = 'stock.value.report.detail'
    _description = 'Stock Value Report Detail'

    report_id = fields.Many2one('stock.value.report', 'Report')
    currency_id = fields.Many2one('res.currency')
    product_id = fields.Many2one('product.product', 'Product')
    product_code = fields.Char('Product Code', related="product_id.default_code")
    opening_quantity = fields.Integer('Opening Quantity')
    opening_value = fields.Monetary('Opening Value')
    incoming_quantity = fields.Integer('Incoming Quantity')
    incoming_value = fields.Monetary('Incoming Value')
    odoo_outgoing_quantity = fields.Integer('Outgoing Quantity')
    odoo_outgoing_value = fields.Monetary('Outgoing Value')
    real_outgoing_price_unit = fields.Monetary('Real Outgoing Price Unit')
    real_outgoing_value = fields.Monetary('Real Outgoing Value')
    diff_outgoing_value = fields.Monetary('Different Outgoing Value', compute="_compute_diff_outgoing_value")
    closing_quantity = fields.Integer('Closing Quantity')
    closing_value = fields.Monetary('Closing Value')

    def _compute_diff_outgoing_value(self):
        for item in self:
            item.diff_outgoing_value = item.odoo_outgoing_value - item.real_outgoing_value