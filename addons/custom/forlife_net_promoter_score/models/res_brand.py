from odoo import api, fields, models


class ResBrand(models.Model):
    _inherit = 'res.brand'

    is_nps = fields.Boolean('Create NPS ?', default=True)
