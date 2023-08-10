# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')
    amount_conversion = fields.Float('Số lượng quy đổi', default=1, required=1)

    date_start = fields.Date('Start Date', help="Start date for this vendor price", required=False)
    date_end = fields.Date('End Date', help="End date for this vendor price", required=False)

    @api.constrains('partner_id', 'product_tmpl_id', 'product_id', 'date_start', 'date_end', 'amount_conversion', 'price', 'product_uom')
    def constrains_supplier(self):
        for rec in self:
            if rec.partner_id and rec.product_tmpl_id and rec.product_id and rec.date_start and rec.date_end and rec.amount_conversion and rec.price and rec.product_uom and rec.search_count(
                    [('partner_id', '=', rec.partner_id.id),
                     '|', ('product_tmpl_id', '=', rec.product_tmpl_id.id),
                     ('product_id', '=', rec.product_id.id),
                     ('date_start', '=', rec.date_start),
                     ('date_end', '=', rec.date_end),
                     ('amount_conversion', '=', rec.amount_conversion),
                     ('price', '=', rec.price),
                     ('product_uom', '=', rec.product_uom.id)]) > 1:
                raise ValidationError(_('Bảng giá nhà cung cấp đã tồn tại!'))

    @api.constrains('amount_conversion')
    def constrains_amount_conversion(self):
        for rec in self:
            if rec.amount_conversion <= 0:
                raise ValidationError(_('Số lượng quy đổi không được nhỏ hơn hoặc bằng 0 !!'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['date_start'] = False
        default['date_end'] = False
        default['min_qty'] = 0
        default['price'] = 0
        return super().copy(default)

    @api.constrains('amount_conversion')
    def _check_amount_conversion_positive(self):
        for record in self:
            if record.amount_conversion < 0:
                raise models.ValidationError("Số lượng quy đổi phải là số dương!")

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Nhập bảng giá nhà cung cấp'),
            'template': '/forlife_purchase/static/src/xlsx/banggianhacungcap.xlsx'
        }]
