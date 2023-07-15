# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _rec_names_search = ['internal_code', 'display_name', 'email', 'ref', 'vat', 'company_registry', 'phone', 'mobile']

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')

    code = fields.Char(string='Code')  # Mã quản lý nhà cung cấp
    internal_code = fields.Char(string='Internal code')  # Mã theo dõi nội bộ
    supplier_group = fields.Many2one('res.supplier.group')
    product_category_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id, group_expand='_read_group_categ_id',
        required=True)
    is_passersby = fields.Boolean(default=False)
    is_inter_company_purchase = fields.Boolean(default=False)

    @api.onchange('internal_code')
    def onchange_is_inter_company_purchase(self):
        for item in self:
            code = str(item.internal_code)
            item.is_inter_company_purchase = True if code.startswith("3000") else False
