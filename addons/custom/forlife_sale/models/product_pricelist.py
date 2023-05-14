from odoo import api, fields, models


class ProductPriceList(models.Model):
    _inherit = 'product.pricelist'

    x_punish = fields.Boolean(string='Bảng giá phạt')
    x_partner_id = fields.Many2one('res.partner', string='Khách hàng')
