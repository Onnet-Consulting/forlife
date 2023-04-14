# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')
    uom_product_tmpl = fields.Many2one(related="product_tmpl_id.uom_id")
    uom_product = fields.Many2one(related="product_id.uom_id")
    amount_conversion = fields.Float('Số lượng quy đổi')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['date_start'] = False
        default['date_end'] = False
        default['min_qty'] = 0
        default['price'] = 0
        return super().copy(default)

    @api.constrains('product_tmpl_id', 'date_start', 'date_end', 'partner_id')
    def constrains_check_duplicate_date_by_product_tmpl_id(self):
        for record in self:
            if record.partner_id and record.product_id and record.product_tmpl_id and record.uom_product and record.date_start and record.date_end and record.uom_product_tmpl and record.search_count(
                    [('date_start', '=', record.date_start),
                     ('date_end', '=', record.date_end),
                     ('partner_id', '=', record.partner_id.id),
                     ('uom_product_tmpl', '=', record.uom_product_tmpl.id),
                     ('uom_product', '=', record.uom_product.id),
                     ('product_id', '=', record.product_id.id),
                     ('product_tmpl_id', '=', record.product_tmpl_id.id),
                     ('id', '!=', record.id)]) > 1:
                raise ValidationError(_('Bảng giá nhà cung cấp đã tồn tại sản phẩm !!'))
