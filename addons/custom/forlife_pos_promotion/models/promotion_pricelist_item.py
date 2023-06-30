# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression
from odoo.tools import float_repr


class PromotionPricelistItem(models.Model):
    _name = 'promotion.pricelist.item'
    _description = 'Promotion Pricelist Item'

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(
        'promotion.program', string='Promotion Program', ondelete='cascade', required=True,
        domain="[('promotion_type', '=', 'pricelist')]")
    product_id = fields.Many2one('product.product', string='Product', domain="[('available_in_pos', '=', True)]",
                                 required=True)
    fixed_price = fields.Float('Fix price')
    barcode = fields.Char(related='product_id.barcode')
    qty_available = fields.Float(related='product_id.qty_available')

    @api.constrains('program_id', 'program_id')
    def check_unique_product_id(self):
        for line in self:
            if len(line.program_id.pricelist_item_ids.filtered(lambda l: l.product_id.id == line.product_id.id)) > 1:
                raise UserError(_('Product %s is already defined in this program!') % line.product_id.name)

    def name_get(self):
        res = []
        result = []
        for line in self:
            name = line.program_id.name + ': ' + \
                   (line.product_id.barcode and '[' + line.product_id.barcode + ']' + ' ' or '') + \
                   line.product_id.name + ': ' +\
                   tools.format_amount(self.env, line.fixed_price, line.program_id.currency_id)
            res += [(line.id, name)]
        return res
