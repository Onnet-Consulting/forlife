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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_get_domain(self):
        if self.order_id.x_sale_type and self.order_id.x_sale_type in ('product', 'service'):
            domain = [('product_type', '=', self.order_id.x_sale_type)]
            return {'domain': {'product_id': [('sale_ok', '=', True), '|', ('company_id', '=', False),
                                              ('company_id', '=', self.order_id.company_id)] + domain}}
