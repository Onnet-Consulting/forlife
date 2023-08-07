# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from . import bkav_action
from odoo.exceptions import ValidationError


class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    is_check_cancel = fields.Boolean(default=False, copy=False, string="Đã hủy")
    is_general = fields.Boolean(default=False, copy=False, string="Đã chạy tổng hợp cuối ngày")
    company_type = fields.Selection(related="partner_id.company_type")
    sequence = fields.Integer(string='Sequence',
                              default=lambda self: self.env['ir.sequence'].next_by_code('account.move.sequence'))

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=True,
                                  copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_form = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date = fields.Date('Ngày HDDT', copy=False)

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

    origin_move_id = fields.Many2one('account.move', 'Hóa đơn gốc')
    po_source_id = fields.Many2one('purchase.order', 'Purchase Order', readonly=True)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['issue_invoice_type'] = 'adjust'
        default['origin_move_id'] = self.id
        return super().copy(default)

    def _get_vat_line_bkav(self,vat_id, price_unit):
        vat = 0
        if vat_id:
            vat = vat_id.amount
            if vat_id.price_include:
                price_unit = price_unit/(1+vat_id.amount/100)
        if vat == 0:
            tax_rate_id = 1
        elif vat == 5:
            tax_rate_id = 2
        elif vat == 8:
            tax_rate_id = 9
        elif vat == 10:
            tax_rate_id = 3
        else:
            tax_rate_id = 4
        return vat, tax_rate_id


    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:            
            if datetime.now().time().hour >= 17:
                invoice_date = datetime.combine(invoice.invoice_date, (datetime.now() - timedelta(hours=17)).time())
            else:
                invoice_date = datetime.combine(invoice.invoice_date, (datetime.now() + timedelta(hours=7)).time())
            list_invoice_detail = []
            exchange_rate = invoice.exchange_rate or 1.0
            for line in invoice.invoice_line_ids:
                item_name = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else '' 
                vat_id = False
                if line.tax_ids:
                    vat_id = line.tax_ids[0]
                vat, tax_rate_id, price_unit = self._get_vat_line_bkav(vat_id, line.price_unit)                                                                                                                                                                             
                item = {
                    "ItemName": item_name,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": abs(line.quantity) or 0.0,
                    "Price": abs(price_unit),
                    "Amount": abs(line.price_subtotal),
                    "TaxAmount": abs((line.tax_amount or 0.0)),
                    "ItemTypeID": 0,
                    # "DiscountRate": line.discount/100,
                    # "DiscountAmount": round(line.price_subtotal/(1+line.discount/100) * line.discount/100),
                    "IsDiscount": 0
                }
                item.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                if invoice.issue_invoice_type == 'adjust':
                    item['IsIncrease'] = 1 if (invoice.move_type == invoice.origin_move_id.move_type) else 0
                list_invoice_detail.append(item)

                
            BuyerName = invoice.partner_id.name if invoice.partner_id.name else ''
            BuyerTaxCode =invoice.partner_id.vat if invoice.partner_id.vat else ''
            if invoice.invoice_info_tax_number:
                BuyerTaxCode = invoice.invoice_info_tax_number

            BuyerUnitName = invoice.partner_id.name if invoice.partner_id.name else ''
            if invoice.invoice_info_company_name:
                BuyerUnitName = invoice.invoice_info_company_name

            BuyerAddress = invoice.partner_id.contact_address_complete if invoice.partner_id.contact_address_complete else ''
            if invoice.invoice_info_address:
                BuyerAddress = invoice.invoice_info_address

            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": BuyerName,
                    "BuyerTaxCode": BuyerTaxCode,
                    "BuyerUnitName": BuyerUnitName,
                    "BuyerAddress": BuyerAddress,
                    "BuyerBankAccount": invoice.partner_bank_id.id if invoice.partner_bank_id.id else '',
                    "PayMethodID": 3,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": invoice.company_id.email if invoice.company_id.email else '',
                    "ReceiverMobile": invoice.company_id.mobile if invoice.company_id.mobile else '',
                    "ReceiverAddress": invoice.company_id.street if invoice.company_id.street else '',
                    "ReceiverName": invoice.company_id.name if invoice.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": invoice.currency_id.name if invoice.currency_id.name else invoice.company_id.currency_id.name,
                    "ExchangeRate": exchange_rate,
                    "InvoiceForm": "1",
                    "InvoiceSerial": invoice.invoice_serial if invoice.invoice_serial else "",
                    "InvoiceNo": invoice.invoice_no if invoice.invoice_no else 0,
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def _check_info_before_bkav(self):
        if self.is_general:
            return False
        #HD ban hang thong thuong
        so_orders = self.invoice_line_ids.sale_line_ids.order_id
        origin_so_orders = False
        if self.origin_move_id:
            origin_so_orders = self.origin_move_id.invoice_line_ids.sale_line_ids.order_id
        if self.move_type in ('out_invoice', 'out_refund') and (so_orders or origin_so_orders):
            return True
        #HD ban le
        pos_orders = self.pos_order_id
        origin_pos_orders = False
        if self.origin_move_id:
            origin_pos_orders = self.origin_move_id.pos_order_id
        if self.move_type in ('out_invoice', 'out_refund') and (pos_orders or origin_pos_orders):
            return False
        #HD tra hang NCC
        pr_orders = self.invoice_line_ids.purchase_line_id.order_id
        origin_pr_orders = False
        if self.origin_move_id:
            origin_pr_orders = self.origin_move_id.invoice_line_ids.purchase_line_id.order_id
        if self.move_type == 'in_refund' and (pr_orders or origin_pr_orders):
            return True
        if self.issue_invoice_type != 'vat':
            if not self.origin_move_id:
                raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh/thay thế')
            if not self.origin_move_id.exists_bkav:
                raise ValidationError('Hóa đơn gốc chưa tồn tại trên hệ thống HDDT BKAV! Vui lòng về đơn gốc kiểm tra!')
            return True
        return True

    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def get_invoice_identify(self):
        return bkav_action.get_invoice_identify(self)

    def get_invoice_status(self):
        return bkav_action.get_invoice_status(self)
    
    def create_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        if self.issue_invoice_type == 'adjust':
            if not self.origin_move_id or not self.origin_move_id.invoice_no:
                raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh')
            if self.origin_move_id.amount_total == self.amount_total:
                self.origin_move_id.cancel_invoice_bkav()
                self.exists_bkav = True
                return
        data = []
        so_orders = self.invoice_line_ids.sale_line_ids.order_id
        origin_so_orders = False
        if self.origin_move_id:
            origin_so_orders = self.origin_move_id.invoice_line_ids.sale_line_ids.order_id
        pr_orders = self.invoice_line_ids.purchase_line_id.order_id
        origin_pr_orders = False
        if self.origin_move_id:
            origin_pr_orders = self.origin_move_id.invoice_line_ids.purchase_line_id.order_id
        pos_orders = self.pos_order_id
        origin_pos_orders = False
        if self.origin_move_id:
            origin_pos_orders = self.origin_move_id.pos_order_id
        if self.move_type in ('out_invoice', 'out_refund') and (so_orders or origin_so_orders):
            data = self.get_bkav_data_so()
        elif self.move_type == 'in_refund' and (pr_orders or origin_pr_orders):
            data = self.get_bkav_data_pr()
        elif self.move_type in ('out_invoice', 'out_refund') and (pos_orders or origin_pos_orders):
            return
            # data = self.get_bkav_data_pos()
        else:
            data = self.get_bkav_data()
        if self.issue_invoice_type != 'vat':
            if not self.origin_move_id:
                raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh/thay thế')
            if not self.origin_move_id.exists_bkav:
                raise ValidationError('Hóa đơn gốc chưa tồn tại trên hệ thống HDDT BKAV! Vui lòng về đơn gốc kiểm tra!')
        origin_id = self.origin_move_id if self.origin_move_id else False
        is_publish = False
        if self._context.get('is_publish'):
            is_publish = True
        issue_invoice_type = self.issue_invoice_type
        if data:
            return bkav_action.create_invoice_bkav(self,data,is_publish,origin_id,issue_invoice_type)

    def publish_invoice_bkav(self):
        return bkav_action.publish_invoice_bkav(self)
    
    def create_publish_invoice_bkav(self):
        return self.with_context({'is_publish': True}).create_invoice_bkav(self)

    def update_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = []
        so_orders = self.invoice_line_ids.sale_line_ids.order_id
        origin_so_orders = False
        if self.origin_move_id:
            origin_so_orders = self.origin_move_id.invoice_line_ids.sale_line_ids.order_id
        pr_orders = self.invoice_line_ids.purchase_line_id.order_id
        origin_pr_orders = False
        if self.origin_move_id:
            origin_pr_orders = self.origin_move_id.invoice_line_ids.purchase_line_id.order_id
        pos_orders = self.pos_order_id
        origin_pos_orders = False
        if self.origin_move_id:
            origin_pos_orders = self.origin_move_id.pos_order_id
        if self.move_type in ('out_invoice', 'out_refund') and (so_orders or origin_so_orders):
            data = self.get_bkav_data_so()
        elif self.move_type == 'in_refund' and (pr_orders or origin_pr_orders):
            data = self.get_bkav_data_pr()
        elif self.move_type in ('out_invoice', 'out_refund') and (pos_orders or origin_pos_orders):
            return
            # data = self.get_bkav_data_pos()
        else:
            data = self.get_bkav_data()
        if self.issue_invoice_type != 'vat':
            if not self.origin_move_id:
                raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh/thay thế')
            if not self.origin_move_id.exists_bkav:
                raise ValidationError('Hóa đơn gốc chưa tồn tại trên hệ thống HDDT BKAV! Vui lòng về đơn gốc kiểm tra!')
        if data:
            return bkav_action.update_invoice_bkav(self,data)

    def get_invoice_bkav(self):
        return bkav_action.get_invoice_bkav(self)

    def cancel_invoice_bkav(self):
        return bkav_action.cancel_invoice_bkav(self)

    def delete_invoice_bkav(self):
        return bkav_action.delete_invoice_bkav(self)

    def download_invoice_bkav(self):
        return bkav_action.download_invoice_bkav(self)

    # def button_cancel(self):
    #     res = super(AccountMoveBKAV, self).button_cancel()
    #     for item in self:
    #         item.cancel_invoice_bkav()
    #     return res
    
    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(AccountMoveBKAV, self).unlink()
    
