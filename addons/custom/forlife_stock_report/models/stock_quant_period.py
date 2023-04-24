# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockQuantPeriod(models.Model):
    _name = 'stock.quant.period'
    _description = 'Quantity period'

    period_end_date = fields.Date('Period End Date')
    product_id = fields.Many2one('product.product', 'Product')
    product_code = fields.Char('Product code', compute="_compute_product_code")
    currency_id = fields.Many2one('res.currency')
    closing_quantity = fields.Integer('Closing Quantity')
    price_unit = fields.Monetary('Price Unit')
    closing_value = fields.Monetary('Closing Value')

    def _compute_product_code(self):
        for item in self:
            item.product_code = item.product_id.default_code or item.product_id.product_tmpl_id.default_code

