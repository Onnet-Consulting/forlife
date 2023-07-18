# -*- coding: utf-8 -*-
from datetime import timedelta

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
    company_id = fields.Many2one('res.company', 'Company')
    account_id = fields.Many2one('account.account', 'Account')
    account_code = fields.Char('Account Code', related="account_id.code")

    def _compute_product_code(self):
        for item in self:
            item.product_code = item.product_id.default_code or item.product_id.product_tmpl_id.default_code
    #
    # def get_last_date_period(self, max_date):
    #     last_record = self.env['stock.quant.period'].sudo().search([('period_end_date', '<=', max_date)],
    #                                                                order='period_end_date desc', limit=1)
    #     return str(last_record.period_end_date) if last_record else str(max_date.replace(day=1) - timedelta(days=1))
