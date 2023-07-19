from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    reference_code = fields.Char('Mã tham chiếu NCC')