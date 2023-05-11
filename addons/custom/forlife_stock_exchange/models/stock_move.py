from odoo import models, fields, api


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    bom_model = fields.Char(string='BOM Model')
    bom_id = fields.Many2oneReference(string='BOM ID', model_field='bom_model')
