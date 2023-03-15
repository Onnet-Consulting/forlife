# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')

    code = fields.Char(string='Code')  # Mã quản lý nhà cung cấp
    internal_code = fields.Char(string='Internal code')  # Mã theo dõi nội bộ
    supplier_group = fields.Many2one('supplier.group')
    product_category_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id, group_expand='_read_group_categ_id',
        required=True)
    gender = fields.Selection(
        [('male', 'Male'),
         ('female', 'Female'),
         ], string='Gender',
        default='male')
    date_of_birth = fields.Date(string='Date Of Birth')

