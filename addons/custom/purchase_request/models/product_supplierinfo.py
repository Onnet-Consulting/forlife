from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure', related=False, readonly=False, store=1)

    @api.constrains('partner_id', 'product_id', 'product_uom')
    def _constraint_product_supplierinfo_rule(self):
        for rec in self:
            if rec.partner_id and rec.product_id and rec.product_uom and rec.search_count(
                [('partner_id', '=', rec.partner_id.id), ('product_id', '=', rec.product_id.id),
                 ('product_uom', '=', rec.product_uom.id)]) > 1:
                raise ValidationError(_('Vendor Pricelists is existed!'))
