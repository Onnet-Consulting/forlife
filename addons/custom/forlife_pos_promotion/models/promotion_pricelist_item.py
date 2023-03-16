# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression


class PromotionPricelistItem(models.Model):
    _name = 'promotion.pricelist.item'
    _description = 'Promotion Pricelist Item'

    active = fields.Boolean(default=True)
    program_id = fields.Many2one('promotion.program', string='Promotion Program', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', domain="[('available_in_pos', '=', True)]")
    fixed_price = fields.Float('Fix price')

    def name_get(self):
        res = []
        for line in self:
            name = line.program_id.name + ': ' + line.product_id.name
            res += [(line.id, name)]
        return res
