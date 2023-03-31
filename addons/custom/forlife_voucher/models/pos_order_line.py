from odoo import api, fields, models, _


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    x_qty_voucher = fields.Float(string="Created Voucher Quantity", digits='Product Unit of Measure', default=0.0)
    is_voucher_conditional = fields.Boolean('Voucher Conditional', default=False)
