# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')


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
            if record.search_count([('date_start', '=', record.date_start),
                                    ('date_end', '=', record.date_end),
                                    ('partner_id', '=', record.partner_id.id),
                                    ('product_id', '=', record.product_id.id),
                                    ('product_tmpl_id', '=', record.product_tmpl_id.id),
                                    ('id', '!=', record.id)]) > 1:
                raise ValidationError(_('Product already exists at the effective date !!'))