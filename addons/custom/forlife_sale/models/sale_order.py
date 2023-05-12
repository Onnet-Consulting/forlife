# -*- coding: utf-8 -*-


from odoo import api, fields,models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_sale_type = fields.Selection(
        [('product', 'Hàng hóa'),
         ('service', 'Dịnh vụ/Tài sản'),
         ('integrated', 'Tích hợp')],
        string='Loại bán hàng', default='product')
    x_sale_chanel = fields.Selection(
        [('pos', 'Đơn bán hàng POS'),
         ('wholesale', 'Đơn bán buôn'),
         ('intercompany', 'Đơn bán hàng liên công ty'),
         ('online', 'Đơn bán hàng online')],
        string='Kênh bán', default='wholesale')
    x_account_analytic_ids = fields.Many2many('account.analytic.account', string='Trung tâm chi phí')
    x_occasion_code_ids = fields.Many2many('occasion.code', string='Mã vụ việc')


