from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure', related=False, readonly=False, store=1)
    min_qty = fields.Float(
        'Quantity', default=1, required=True, digits="Product Unit Of Measure",
        help="The quantity to purchase from this vendor to benefit from the price, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise.")
    supplier_code = fields.Char(related="partner_id.ref", string="Supplier Code", store=1)

    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            if 'partner_id' in fields:
                fields[fields.index('partner_id')] = 'supplier_code'
        return super().load(fields, data)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('supplier_code') and not val.get('partner_id'):
                partner_id = self.env['res.partner'].search([('ref', '=', val.get('supplier_code'))], limit=1).id
                val.update({
                    'partner_id': partner_id
                })
        return super(SupplierInfo, self).create(vals)

    @api.onchange('product_tmpl_id')
    def onchange_product_uom(self):
        if self.product_tmpl_id:
            self.product_uom = self.product_tmpl_id.uom_po_id.id
