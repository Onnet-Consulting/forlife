# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_open_quant_period(self):
        return self.product_variant_ids.action_open_quant_period()
