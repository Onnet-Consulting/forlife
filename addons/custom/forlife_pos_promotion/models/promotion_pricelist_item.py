# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
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
    lst_price = fields.Float('Sale Price', related='product_id.lst_price', digits='Product Price')
    fixed_price = fields.Float('Fix price')
    barcode = fields.Char(related='product_id.barcode')
    qty_available = fields.Float(related='product_id.qty_available')
    with_code = fields.Boolean(related='program_id.with_code')
    reward_type = fields.Selection(related='program_id.reward_type')

    # @api.constrains('program_id', 'program_id')
    # def check_unique_product_id(self):
    #     for line in self:
    #         if len(line.program_id.pricelist_item_ids.filtered(lambda l: l.product_id.id == line.product_id.id)) > 1:
    #             raise UserError(_('Product %s is already defined in this program!') % line.product_id.name)

    @api.constrains('program_id', 'product_id')
    def check_unique_product(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('program_id', 'in', self.program_id.ids)]
        search_fields = ['program_id', 'product_id']
        groupby = ['program_id', 'product_id']
        records = self.with_context(active_test=False)._read_group(domain, search_fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(rec['product_id'][0]).display_name
                program_name = self.env['promotion.program'].browse(rec['program_id'][0]).display_name
                error_message_lines.append(_(" - %s trong Chương trình: %s", product_name, program_name))
        if error_message_lines:
            raise ValidationError(_('Các sản phẩm đã được thiết lập:\n') + '\n'.join(error_message_lines))

    def name_get(self):
        res = []
        result = []
        for line in self:
            name = line.program_id.name + ': ' + \
                   (line.product_id.barcode and '[' + line.product_id.barcode + ']' + ' ' or '') + \
                   line.product_id.name + ': ' +\
                   tools.format_amount(self.env, line.fixed_price, line.program_id.currency_id)
            res += [(line.id, name)]
        if 'show_price' in self._context and self._context.get('show_price'):
            for line in self:
                record_name = str(line.fixed_price)
                result.append((line.id, record_name))
            return result
        return res
