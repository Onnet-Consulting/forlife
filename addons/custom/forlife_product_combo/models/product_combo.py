# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'product combo'

    code = fields.Char('Combo code', readonly=True, copy=False, default='New')
    description_combo = fields.Text(string="Description combo")
    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished')),
        ('canceled', _('Canceled'))], string='State', default='new')
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    combo_product_ids = fields.One2many('product.combo.line', 'combo_id', string='Combo Applied Products')
    size_attribute_id = fields.Many2one('product.attribute', string="Size Deviation Allowed", domain="[('create_variant', '=', 'always'), ('id', '!=', color_attribute_id)]")
    color_attribute_id = fields.Many2one('product.attribute', string="Color Deviation Allowed", domain="[('create_variant', '=', 'always'), ('id', '!=', size_attribute_id)]")

    _sql_constraints = [
        ('combo_check_date', 'CHECK(from_date <= to_date)', 'End date may not be before the starting date.')]


    @api.model_create_multi
    def create(self, vals):

        vals['code'] = self.env['ir.sequence'].next_by_code('product.combo')
        result = super(ProductCombo, self).create(vals)
        for pr in result.combo_product_ids:
            pr.product_id.write({
                'combo_id': result.id if vals['state'] in ['in_progress'] else None
            })

        return result

    def write(self, values):
        res = super().write(values)
        for pr in self.combo_product_ids:
            pr.product_id.write({
                'combo_id': self.id if self.state in ['in_progress'] else None
            })
        return res
