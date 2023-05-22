# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_brand_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.brand_default_id

    brand_id = fields.Many2one('res.brand', string='Brand', default=_get_brand_default)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_id = fields.Many2one('res.brand', related='product_tmpl_id.brand_id', string='Brand', readonly=1)
