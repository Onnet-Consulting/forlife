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

    @api.depends('category_type_id', 'product_brand_id', 'product_group_ids', 'product_line_ids', 'texture_ids')
    def _compute_category_domain(self):
        Utility = self.env['res.utility']
        for line in self:
            category_domain = [('type', '=', 'product')]
            categ_ids = line.texture_ids or line.product_line_ids or line.product_group_ids or line.product_brand_id
            if categ_ids:
                category_domain += [('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]
            line.category_domain = json.dumps(category_domain)

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
