# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from . import bkav_action

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

    origin_move_id = fields.Many2one('account.move', 'Hóa đơn gốc')
    po_source_id = fields.Many2one('purchase.order', 'Purchase Order', readonly=True)

    def write(self, vals):
        res = super(AccountMoveBKAV, self).write(vals)
        if vals.get('po_source_id') and self.state == 'posted':
            if self.po_source_id.is_inter_company:
                self.create_an_invoice_and_publish_invoice_bkav()
        return res


    def create_an_invoice_and_publish_invoice_bkav(self):
        for invoice in self:
            try:
                invoice.create_invoice_bkav()
            except Exception as e:
                pass


    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            sale_order_id = invoice.invoice_line_ids.sale_line_ids.order_id
            if not sale_order_id:
                continue
            
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            for line in sale_order_id.order_line:
                #SP Voucher k đẩy BKAV
                if line.product_id.voucher:continue
                item_name = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else ''
                vat = 0
                if line.tax_id:
                    vat = line.tax_id[0].amount
                Qty = round(line.price_total/ (line.product_uom_qty * (1 + vat/100)))
                Amount = Qty * line.product_uom_qty
                item = {
                    "ItemName": item_name if not line.x_free_good else item_name + " (Hàng tặng không thu tiền)",
                    "UnitName": line.product_uom.name or '',
                    "Qty": Qty,
                    "Price": round(line.price_total/ (line.product_uom_qty * (1 + vat/100))),
                    "Amount": Amount,
                    "TaxAmount": (line.price_total-  Amount or 0.0),
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": line.price_total * line.discount/100,
                    "IsDiscount": 1 if line.x_free_good else 0
                }
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
                item.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                if invoice.issue_invoice_type == 'adjust':
                    # kiểm tra hóa đơn gốc
                    # gốc là out_invoice => điều chỉnh giảm
                    # gốc là out_refund => điều chỉnh tăng
                    item['IsIncrease'] = invoice.origin_move_id.move_type != 'out_invoice'

                list_invoice_detail.append(item)
            reward_amount = sum(sale_order_id.promotion_ids.filtered(lambda x:x.promotion_type =='reward').mapped('value'))
            if reward_amount != 0:
                item = {
                    "ItemName": 'Chiết khấu tổng đơn',
                    "UnitName": '',
                    "Qty": 1.0,
                    "Price": abs(reward_amount),
                    "Amount": abs(reward_amount),
                    "TaxAmount": 0,
                    "ItemTypeID": 0,
                    "IsDiscount": 1
                }

                list_invoice_detail.append(item)
            vip_amount = sum(sale_order_id.promotion_ids.filtered(lambda x:x.promotion_type =='vip_amount').mapped('value'))
            if vip_amount != 0:
                item = {
                    "ItemName": 'Chiết khấu hạng thẻ',
                    "UnitName": '',
                    "Qty": 1.0,
                    "Price": abs(vip_amount),
                    "Amount": abs(vip_amount),
                    "TaxAmount": 0,
                    "ItemTypeID": 0,
                    "IsDiscount": 1
                }
                list_invoice_detail.append(item)
                
            BuyerName = invoice.partner_id.name if invoice.partner_id.name else ''
            if invoice.invoice_info_company_name:
                BuyerName = invoice.invoice_info_company_name

            BuyerTaxCode =invoice.partner_id.vat if invoice.partner_id.vat else ''
            if invoice.invoice_info_tax_number:
                BuyerTaxCode = invoice.invoice_info_tax_number

            BuyerUnitName = invoice.partner_id.name if invoice.partner_id.name else ''
            if invoice.invoice_info_company_name:
                BuyerUnitName = invoice.invoice_info_company_name

            BuyerAddress = invoice.partner_id.country_id.name if invoice.partner_id.country_id.name else ''
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
                    "PayMethodID": 1,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": invoice.company_id.email if invoice.company_id.email else '',
                    "ReceiverMobile": invoice.company_id.mobile if invoice.company_id.mobile else '',
                    "ReceiverAddress": invoice.company_id.street if invoice.company_id.street else '',
                    "ReceiverName": invoice.company_id.name if invoice.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": invoice.company_id.currency_id.name if invoice.company_id.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def _check_info_before_bkav(self):
        if not self.is_general:
            return True
        #HD ban hang thong thuong
        so_orders = self.invoice_line_ids.sale_line_ids.order_id
        if self.move_type in ('out_invoice', 'out_refund') and so_orders:
            return True
        #HD tra hang NCC
        po_orders = self.invoice_line_ids.purchase_line_id.order_id
        if self.move_type == 'in_refund' and po_orders:
            return True
        return False

    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def get_invoice_identify(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_identify(self)

    def get_invoice_status(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_status(self)
    
    def create_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        if self.move_type in ('out_invoice', 'out_refund'):
            data = self.get_bkav_data()
        elif self.move_type == 'in_refund':
            data = self.get_bkav_data_po()
        origin_id = self.origin_move_id if self.origin_move_id else False
        is_publish = True
        issue_invoice_type = self.issue_invoice_type
        return bkav_action.create_invoice_bkav(self,data,is_publish,origin_id,issue_invoice_type)

    def publish_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.publish_invoice_bkav(self)

    def update_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = self.get_bkav_data()
        return bkav_action.create_invoice_bkav(self,data)

    def get_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_bkav(self)

    def cancel_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        PartnerInvoiceID = self.id,
        PartnerInvoiceStringID = ''
        return bkav_action.cancel_invoice_bkav(self,PartnerInvoiceID,PartnerInvoiceStringID)

    def delete_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        PartnerInvoiceID = self.id,
        PartnerInvoiceStringID = ''
        return bkav_action.delete_invoice_bkav(self,PartnerInvoiceID,PartnerInvoiceStringID)

    def download_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.download_invoice_bkav(self)

    def action_cancel(self):
        res = super(AccountMoveBKAV, self).action_cancel()
        self.cancel_invoice_bkav()
        return res
    
    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(AccountMoveBKAV, self).unlink()
    
    