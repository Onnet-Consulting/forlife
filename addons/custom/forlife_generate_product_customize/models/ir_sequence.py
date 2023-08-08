from odoo import api, fields, models


class IrSequene(models.Model):
    _inherit = 'ir.sequence'

    sku_code = fields.Char('SKU-CODE')