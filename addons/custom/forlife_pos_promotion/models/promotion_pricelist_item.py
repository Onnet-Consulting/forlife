# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression


class PromotionPricelistItem(models.Model):
    _name = 'promotion.pricelist.item'

    active = fields.Boolean(default=True)
    program_id = fields.Many2one('promotion.program', string='Promotion Program', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', domain="[('available_in_pos', '=', True)]")
    fixed_price = fields.Float('Fix price')
