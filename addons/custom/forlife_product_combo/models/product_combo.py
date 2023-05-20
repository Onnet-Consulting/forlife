# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'product combo'

    code = fields.Char('Combo code', readonly=True, required=True, copy=False, default='New')
    description_combo = fields.Text(string="Description combo")
    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished')),
        ('canceled', _('Canceled'))], string='State', default='new')
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    size_deviation_allowed = fields.Boolean('Size Deviation Allowed')
    color_deviation_allowed = fields.Boolean('Color Deviation Allowed')
    combo_product_ids = fields.One2many('product.combo.line', 'combo_id', string='Combo Applied Products')

    _sql_constraints = [
        ('combo_check_date', 'CHECK(from_date <= to_date)', 'End date may not be before the starting date.')]



    @api.model
    def create(self, vals):

        vals['code'] = self.env['ir.sequence'].next_by_code('product.combo')
        result = super(ProductCombo, self).create(vals)
        for pr in result.combo_product_ids:
            pr.product_id.write({
                'combo_id': result.id if vals['state'] in ['in_progress'] else None
            })
            pr.product_id.product_variant_id.write({
                'combo_id': self.id if self.state in ['in_progress'] else None
            })

        return result

    def write(self, values):
        res = super().write(values)
        for pr in self.combo_product_ids:
            pr.product_id.write({
                'combo_id': self.id if self.state in ['in_progress'] else None
            })
            pr.product_id.product_variant_id.write({
                'combo_id': self.id if self.state in ['in_progress'] else None
            })
        return res