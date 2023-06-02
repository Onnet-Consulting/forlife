# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(related='partner_id.code')
    amount_conversion = fields.Float('Số lượng quy đổi')

    date_start = fields.Date('Start Date', help="Start date for this vendor price", required=True)
    date_end = fields.Date('End Date', help="End date for this vendor price", required= True)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['date_start'] = False
        default['date_end'] = False
        default['min_qty'] = 0
        default['price'] = 0
        return super().copy(default)

    # @api.constrains('product_tmpl_id', 'date_start', 'date_end', 'partner_id', 'product_id', 'min_qty', 'amount_conversion', 'product_uom', 'price', 'currency_id')
    # def constrains_check_duplicate_date_by_product_tmpl_id(self):
    #     if self.partner_id and self.product_id and self.min_qty and self.amount_conversion and self.price and self.currency_id and self.product_tmpl_id \
    #             and self.product_uom and self.date_start and self.date_end:
    #         a = self.search([('partner_id', '=', self.partner_id.id),
    #                          ('product_uom', '=', self.product_uom.id),
    #                          ('currency_id', '=', self.currency_id.id),
    #                          ('product_id', '=', self.product_id.id),
    #                          ('product_tmpl_id', '=', self.product_tmpl_id.id)], limit=1)
    #         b = self.search([('partner_id', '=', self.partner_id.id),
    #                          ('product_uom', '=', self.product_uom.id),
    #                          ('currency_id', '=', self.currency_id.id),
    #                          ('product_id', '=', self.product_id.id),
    #                          ('product_tmpl_id', '=', self.product_tmpl_id.id),
    #                          ('id', '!=', a.id)
    #                          ])
    #         for item in b:
    #             if a:
    #                 if item.date_end == a.date_end and item.date_start == a.date_start:
    #                     raise ValidationError('lỗi')
    #                 elif item.date_end < a.date_end and item.date_start <= a.date_start:
    #                     raise ValidationError('lỗi')
    #             # raise ValidationError(_('Bảng giá nhà cung cấp đã tồn tại sản phẩm !!'))
    #         # for record_2 in self:
    #         #     if record != record_2 and record.partner_id.id == record_2.partner_id.id and record.product_id.id == record_2.product_id.id and record.currency_id.id == record_2.currency_id.id and record.product_tmpl_id.id == record_2.product_tmpl_id.id and record.product_uom.id == record_2.product_uom.id:
    #         #         if record.date_start <= record_2.date_start <= record.date_end:
    #         #             raise ValidationError(_('Đã tồn tại bản ghi nhà cung cấp chứa sản phẩm này trong khoảng thời gian %s tới %s') %(record.date_start, record.date_end))
    #         #         else:
    #         #             pass
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
