from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure', related=False, readonly=False, store=1)
    min_qty = fields.Float(
        'Quantity', default=1, required=True, digits="Product Unit Of Measure",
        help="The quantity to purchase from this vendor to benefit from the price, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise.")

    @api.onchange('product_tmpl_id')
    def onchange_product_uom(self):
        if self.product_tmpl_id:
            self.product_uom = self.product_tmpl_id.uom_po_id.id