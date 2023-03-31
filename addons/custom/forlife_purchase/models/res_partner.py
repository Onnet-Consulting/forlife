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
    gender = fields.Selection(
        [('male', 'Male'),
         ('female', 'Female'),
         ], string='Gender',
        default='male')
    is_passersby = fields.Boolean(defaul=False)
    is_inter_company_purchase = fields.Boolean(default=False)

    @api.onchange('internal_code')
    def onchange_is_inter_company_purchase(self):
        for item in self:
            code = str(item.internal_code)
            item.is_inter_company_purchase = True if code.startswith("3000") else False
