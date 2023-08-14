# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResSupplierGroup(models.Model):
    _name = 'res.supplier.group'
    _inherit = "forlife.model.mixin"
    _description = "Supplier Group"


class SupplierProductType(models.Model):
    _name = 'supplier.product.type'
    _inherit = "forlife.model.mixin"
    _description = "Type of Supplier Product"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    supplier_group_id = fields.Many2one('res.supplier.group', string="Supplier Group", copy=False)
    sup_product_type_id = fields.Many2one('supplier.product.type', string="Type of Supplier Product", copy=False)

