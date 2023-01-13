from odoo import api, fields, models, _


class ForLifeResPartner(models.Model):
    _inherit = "res.partner"

    internal_code = fields.Char(string="Internal Code")
    supplier_group = fields.Many2one('supplier.group')
