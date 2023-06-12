# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')
    amount_conversion = fields.Float('Số lượng quy đổi', default=1, required=1)

    date_start = fields.Date('Start Date', help="Start date for this vendor price", required=True)
    date_end = fields.Date('End Date', help="End date for this vendor price", required=True)

    @api.constrains('product_tmpl_id', 'date_start', 'date_end', 'partner_id')
    def constrains_check_duplicate_date_by_product_tmpl_id(self):
        for record in self:
            if record.partner_id and record.product_id and record.product_tmpl_id and record.product_uom and record.date_start and record.date_end and record.search_count(
                    [('date_start', '=', record.date_start),
                     ('date_end', '=', record.date_end),
                     ('partner_id', '=', record.partner_id.id),
                     ('currency_id', '=', record.currency_id.id),
                     ('product_uom', '=', record.product_uom.id),
                     ('product_id', '=', record.product_id.id),
                     ('product_tmpl_id', '=', record.product_tmpl_id.id),
                     ('id', '!=', record.id)]) > 1:
                raise ValidationError(_('Bảng giá nhà cung cấp đã tồn tại sản phẩm !!'))

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
