from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_qty_voucher = fields.Float(string="Created Voucher Quantity", digits='Product Unit of Measure', default=0.0)

    @api.onchange('price_unit')
    def onchange_validate_voucher_price(self):
        if not self.price_unit or not self.product_id.voucher:
            return
        if self.price_unit > self.product_id.price:
            raise ValidationError(_("Price unit cannot be higher than Voucher's price"))
