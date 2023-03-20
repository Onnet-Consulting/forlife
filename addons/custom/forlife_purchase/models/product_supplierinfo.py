# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')

