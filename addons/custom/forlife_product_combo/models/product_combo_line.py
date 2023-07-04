# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductComboLine(models.Model):
    _name = 'product.combo.line'
    _description = 'product combo Line'

    sku = fields.Char(string="SKU", related='product_id.sku_code', store=True)
    combo_id = fields.Many2one('product.combo')
    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished')),
        ('canceled', _('Canceled'))], string='State', default='new', related='combo_id.state', store=True)
    product_id = fields.Many2one('product.template', string='Product', required=True, domain="[('available_in_pos', '=', True)]")
    quantity = fields.Float('Quantity')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', store=True)

