# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json
from odoo.tools.safe_eval import safe_eval


class FilterProductWizard(models.Model):
    _name = 'filter.product.wizard'
    _inherit = 'report.category.type'
    _description = 'Lọc sản phẩm'
    _order = 'id desc'

    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    product_group_ids = fields.Many2many('product.category', 'filter_product_wizard_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'filter_product_wizard_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'filter_product_wizard_texture_rel', string='Level 4')
    category_domain = fields.Char('Products', compute='_compute_category_domain')

    @api.depends('category_level', 'category_type_id', 'product_brand_id',
                 'product_group_ids', 'product_line_ids', 'texture_ids')
    def _compute_category_domain(self):
        for line in self:
            category_domain = "[('type', '=', 'product')]"
            if line.texture_ids:
                category_domain = line.get_text_domain(line.texture_ids, line.category_level, 4)
            elif line.product_line_ids:
                category_domain = line.get_text_domain(line.product_line_ids, line.category_level, 3)
            elif line.product_group_ids:
                category_domain = line.get_text_domain(line.product_group_ids, line.category_level, 2)
            elif line.product_brand_id:
                category_domain = line.get_text_domain(line.product_brand_id, line.category_level, 1)
            line.category_domain = category_domain

    @api.model
    def get_text_domain(self, categ_ids, category_level, current_level):
        _mapped = ['child_id'] * (category_level - current_level)
        return json.dumps([('categ_id', 'in', categ_ids.mapped('.'.join(_mapped)).ids if _mapped else categ_ids.ids), ('type', '=', 'product')])

    @api.onchange('product_brand_id')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_id.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

    def action_confirm(self):
        self.inventory_id.product_ids = self.env['product.product'].search(safe_eval(self.category_domain or "[('id', '=', 0)]"))



