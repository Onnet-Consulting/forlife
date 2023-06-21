from odoo import api, fields, models

class ProductToleranceLine(models.Model):
    _name = 'product.tolerance.line'

    _description = 'Details Tolerance of vendor'

    product_id = fields.Many2one('product.template')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    tolerance = fields.Float('Tolerance (%)')