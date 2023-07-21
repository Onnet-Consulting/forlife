# -*- coding: utf-8 -*-
#By TienNQ

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
import json
from ...bkav_connector.models.bkav_connector import connect_bkav
from ...bkav_connector.models import bkav_action

_logger = logging.getLogger(__name__)

disable_create_function = False


class PosOrderBKAV(models.Model):
    _inherit = 'pos.order'

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    is_check_cancel = fields.Boolean(default=False, copy=False, string="Đã hủy")
    is_general = fields.Boolean(default=False, copy=False, string="Đã chạy tổng hợp cuối ngày")
    company_type = fields.Selection(related="partner_id.company_type")
    sequence = fields.Integer(string='Sequence',
                              default=lambda self: self.env['ir.sequence'].next_by_code('account.move.sequence'))

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status_get_values', store=1,
                                  copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_form = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date = fields.Datetime('Ngày HDDT', copy=False)

    data_compare_status = fields.Selection([('1', 'Mới tạo'),
                                            ('2', 'Đã phát hành'),
                                            ('3', 'Đã hủy'),
                                            ('4', 'Đã xóa'),
                                            ('5', 'Chờ thay thế'),
                                            ('6', 'Thay thế'),
                                            ('7', 'Chờ điều chỉnh'),
                                            ('8', 'Điều chỉnh'),
                                            ('9', 'Bị thay thế'),
                                            ('10', 'Bị điều chỉnh'),
                                            ('11', 'Trống (Đã cấp số, Chờ ký)'),
                                            ('12', 'Không sử dụng'),
                                            ('13', 'Chờ huỷ'),
                                            ('14', 'Chờ điều chỉnh chiết khấu'),
                                            ('15', 'Điều chỉnh chiết khấu')], copy=False)

    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)
    issue_invoice_type = fields.Selection([
        ('vat', 'GTGT'),
        ('adjust', 'Điều chỉnh'),
        ('replace', 'Thay thế')
    ], 'Loại phát hành', default='vat', required=True)    

    is_post_bkav_store = fields.Boolean(string='Có phát hành hóa đơn bkav', related='store_id.is_post_bkav')
    

    @api.depends('data_compare_status')
    def _compute_data_compare_status_get_values(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)


    def get_invoice_identify(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_identify(self)

    def getting_invoice_status(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.getting_invoice_status(self)
    
    def _check_info_before_bkav(self):
        if not self.invoice_info_company_name or not self.invoice_info_address or not self.invoice_info_tax_number:
            return False
        if not self.store_id.is_post_bkav:
            return False
        return True


    def get_bkav_data(self):
        bkav_data = []
        for pos in self:
            invoice_date = fields.Datetime.context_timestamp(pos, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            for line in pos.lines:
                item_name = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else ''
                item = {
                    "ItemName": item_name,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.qty or 0.0,
                    "Price": (line.price_unit - line.price_unit * line.discount / 100),
                    "Amount": line.price_subtotal,
                    "TaxAmount": (line.price_subtotal_incl - line.price_subtotal or 0.0),
                    "ItemTypeID": 0,
                    "IsDiscount": line.discount/100,
                }
                if line.tax_ids:
                    if line.tax_ids[0].amount == 0:
                        tax_rate_id = 0
                    elif line.tax_ids[0].amount == 5:
                        tax_rate_id = 1
                    elif line.tax_ids[0].amount == 10:
                        tax_rate_id = 3
                    else:
                        tax_rate_id = 6
                    item.update({
                        "TaxRateID": tax_rate_id,
                        "TaxRate": line.tax_ids[0].amount
                    })
                # if pos.issue_invoice_type == 'edit':
                #     # kiểm tra hóa đơn gốc
                #     # gốc là out_invoice => điều chỉnh giảm
                #     # gốc là out_refund => điều chỉnh tăng
                #     item['IsIncrease'] = pos.origin_move_id.move_type != 'out_invoice'

                list_invoice_detail.append(item)
            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": pos.invoice_info_company_name,
                    "BuyerTaxCode": pos.invoice_info_tax_number ,
                    "BuyerUnitName": pos.invoice_info_company_name,
                    "BuyerAddress": pos.invoice_info_address,
                    "BuyerBankAccount": '',
                    "PayMethodID": 1,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": pos.company_id.email if pos.company_id.email else '',
                    "ReceiverMobile": pos.company_id.mobile if pos.company_id.mobile else '',
                    "ReceiverAddress": pos.company_id.street if pos.company_id.street else '',
                    "ReceiverName": pos.company_id.name if pos.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": pos.company_id.currency_id.name if pos.company_id.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    # "OriginalInvoiceIdentify": pos.origin_move_id.get_invoice_identify() if pos.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": pos.name,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def create_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        # validate với trường hợp điều chỉnh thay thế
        # if self.issue_invoice_type in ('edit', 'replace') and not self.origin_move_id.invoice_no:
        #     raise ValidationError('Vui lòng chọn hóa đơn gốc cho đã được phát hành để điều chỉnh hoặc thay thế')
        data = self.get_bkav_data()
        return bkav_action.create_invoice_bkav(self,data)


    def publish_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.publish_invoice_bkav(self)

    def update_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        # validate với trường hợp điều chỉnh thay thế
        # if self.issue_invoice_type in ('edit', 'replace') and not self.origin_move_id.invoice_no:
        #     raise ValidationError('Vui lòng chọn hóa đơn gốc cho đã được phát hành để điều chỉnh hoặc thay thế')
        data = self.get_bkav_data()
        return bkav_action.create_invoice_bkav(self,data)

    def get_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_bkav(self)

    def cancel_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.cancel_invoice_bkav(self)

    def delete_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.delete_invoice_bkav(self)

    def download_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.download_invoice_bkav(self)

