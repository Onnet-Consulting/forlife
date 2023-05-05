from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = "product.product"

    is_check_cost = fields.Boolean(default=False, string='Thuộc chi phí')