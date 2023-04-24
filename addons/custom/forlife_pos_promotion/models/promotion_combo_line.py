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
    product_ids = fields.Many2many('product.product', string='Products', domain="[('available_in_pos', '=', True)]")
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
