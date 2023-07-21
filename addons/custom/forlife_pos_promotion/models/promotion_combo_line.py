# -*- coding: utf-8 -*-
import base64
import json

from odoo import _, api, fields, models
from odoo.models import NewId
from odoo.osv import expression


class PromotionComboLine(models.Model):
    _name = 'promotion.combo.line'
    _description = 'Promotion Combo Line'

    program_id = fields.Many2one('promotion.program')
    name = fields.Char(related='program_id.name')
    product_ids = fields.Many2many(
        'product.product', relation='product_product_promotion_combo_line_rel', string='Products',
        domain="[('available_in_pos', '=', True)]")
    product_categ_ids = fields.Many2many('product.category', string='Product Categories')
    quantity = fields.Float()
    valid_product_ids = fields.Many2many('product.product', compute='_compute_valid_product_ids')
    json_valid_product_ids = fields.Binary(
        compute='_compute_json_valid_product_ids', string='Json Valid Products', store=True)

    product_count = fields.Integer(compute='_compute_valid_product_ids', string='Product Counts')

    _sql_constraints = [
        ('combo_line_quantity_check', 'CHECK (quantity > 0)', 'Quantity must be positive'),
    ]

    def _get_valid_product_domain(self):
        self.ensure_one()
        domain = []
        if self.product_ids:
            domain = [('id', 'in', self.product_ids.ids)]
        if self.product_categ_ids:
            for categ in self.product_categ_ids:
                if not isinstance(categ.id, NewId):
                    domain = expression.OR([domain, [('categ_id', 'child_of', categ.id)]])
        return domain

    @api.depends('product_ids', 'product_categ_ids')
    def _compute_valid_product_ids(self):
        for line in self:
            if line.product_ids or line.product_categ_ids:
                domain = line._get_valid_product_domain()
                domain = expression.AND([[('available_in_pos', '=', True)], domain])
                line.valid_product_ids = self.env['product.product'].search(domain)
            else:
                line.valid_product_ids = self.env['product.product']
            line.product_count = len(line.valid_product_ids)

    @api.depends('product_ids', 'product_categ_ids')
    def _compute_json_valid_product_ids(self):
        for line in self:
            product_ids = line.valid_product_ids.ids or []
            product_ids_json_encode = base64.b64encode(json.dumps(product_ids).encode('utf-8'))
            line.json_valid_product_ids = product_ids_json_encode

    def open_products(self):
        action = self.env["ir.actions.actions"]._for_xml_id("product.product_normal_action_sell")
        action['domain'] = [('id', 'in', self.valid_product_ids.ids)]
        return action

    def action_open_combo_line_product(self):
        return {
            'name': _('Combo Line Products') + ((self.name and _(' of %s') % self.name) or ''),
            'domain': [('promotion_combo_line_id', '=', self.id)],
            'res_model': 'promotion.combo.line.product',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': {'default_promotion_combo_line_id': self.id}
        }


class PromotionComboLineProduct(models.Model):
    _name = 'promotion.combo.line.product'
    _description = 'Promotion Reward Product'
    _table = 'product_product_promotion_combo_line_rel'

    product_product_id = fields.Many2one('product.product', required=True, index=True, string='Product')
    promotion_combo_line_id = fields.Many2one('promotion.combo.line', required=True, index=True, string='Combo Line')

    def init(self):
        self.env.cr.execute("""
            ALTER TABLE product_product_promotion_combo_line_rel ADD COLUMN IF NOT EXISTS id SERIAL; """)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._recompute_json_binary_fields()
        return res

    def unlink(self):
        combo_lines = self.promotion_combo_line_id
        res = super(PromotionComboLineProduct, self).unlink()
        if combo_lines:
            combo_lines._compute_json_valid_product_ids()
        return res

    def _recompute_json_binary_fields(self):
        combo_lines = self.env['promotion.combo.line'].search([('id', 'in', self.promotion_combo_line_id.ids)])
        combo_lines._compute_json_valid_product_ids()
