from odoo import models, fields, api


class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    exchange_code = fields.Selection([
        ('incoming', 'Import of finished products'),
        ('outgoing', 'Export of materials')
    ], string='Exchange Code', index=True)

    _sql_constraints = [
        ('exchange_code_uniq', 'unique(exchange_code, company_id)', 'The exchange code must be unique per company!'),
    ]
