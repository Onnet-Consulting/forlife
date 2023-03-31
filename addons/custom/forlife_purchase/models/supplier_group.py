
from odoo import api, fields, models, _


class SupplierGroup(models.Model):
    _name = "supplier.group"
    _rec_name = "name"

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")

