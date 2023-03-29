from odoo import api, fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    code = fields.Char(string='Code')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]
