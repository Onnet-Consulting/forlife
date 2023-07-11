from odoo import api, fields, models
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = 'product.product'

    department_id = fields.Many2one('hr.department', string="Department")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    asset_location_id = fields.Many2one('asset.location', string="Asset Location")
    x_check_npl = fields.Boolean('')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if res.get('detailed_type') and res.get('detailed_type').get("selection"):
            detailed_type = res.get('detailed_type').get("selection")
            for value in detailed_type:
                if value and value[0] == 'consu':
                    detailed_type.remove(value)
        return res

    def _prepare_sellers(self, partner_id=False, uom_id=False, params=False):
        if partner_id and uom_id:
            return self.seller_ids.filtered(
                lambda s: s.partner_id.active and s.partner_id.id == partner_id.id and s.product_uom.id == uom_id.id).sorted(
                lambda s: (s.sequence, -s.min_qty, s.price, s.id))
        else:
            return self.seller_ids.filtered(lambda s: s.partner_id.active).sorted(lambda s: (s.sequence, -s.min_qty, s.price, s.id))

    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        res = self.env['product.supplierinfo']
        sellers = self._prepare_sellers(partner_id, uom_id, params)
        sellers = sellers.filtered(lambda s: not s.company_id or s.company_id.id == self.env.company.id)
        for seller in sellers:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                continue
                # quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.partner_id not in [partner_id, partner_id.parent_id]:
                continue
            if quantity is not None and float_compare(quantity_uom_seller, seller.min_qty, precision_digits=precision) == -1:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            if not res or res.partner_id == seller.partner_id:
                res |= seller
        return res.sorted('price')[:1]
