# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    x_sync_nhanh = fields.Boolean(string='Đồng bộ lên Nhanh.VN', default=False, copy=False)

class ProductTemplateAttributeLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.attribute.value"""
    _inherit = "product.template.attribute.line"

    x_sync_nhanh = fields.Boolean(string='Đồng bộ lên Nhanh.VN', related="attribute_id.x_sync_nhanh")
    