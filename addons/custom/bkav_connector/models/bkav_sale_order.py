# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountMoveSaleOrder(models.Model):
    _inherit = 'account.move'


    def get_bkav_data_so(self):
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
                Price = abs(round(line.price_total/ (line.product_uom_qty * (1 + vat/100))))
                Amount = abs(Price * line.product_uom_qty)
                item = {
                    "ItemName": item_name if not line.x_free_good else item_name + " (Hàng tặng không thu tiền)",
                    "UnitName": line.product_uom.name or '',
                    "Qty": abs(line.product_uom_qty),
                    "Price": Price,
                    "Amount": Amount,
                    "TaxAmount": (abs(line.price_total) -  Amount or 0.0),
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": abs(line.price_total * line.discount/100),
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
                    # gốc là out_refund => điều chỉnh giảm
                    # gốc là out_invoice => điều chỉnh tăng
                    item['IsIncrease'] = 1 if (invoice.move_type == 'out_invoice') else 0

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
                    "IsDiscount": 1,
                    "TaxRateID": 1,
                    "TaxRate": 0,
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
                    "IsDiscount": 1,
                    "TaxRateID": 1,
                    "TaxRate": 0,
                }
                list_invoice_detail.append(item)
                
            BuyerName = invoice.partner_id.name if invoice.partner_id.name else ''
            # if invoice.invoice_info_company_name:
            #     BuyerName = invoice.invoice_info_company_name 

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
                    "PayMethodID": 3,
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
    

    def _post(self, soft=True):
        res = super(AccountMoveSaleOrder, self)._post(soft)
        for item in self:
            if item.issue_invoice_type == 'adjust':
                if not item.origin_move_id or not item.origin_move_id.invoice_no:
                    raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh')
                if item.origin_move_id.amount_total == item.amount_total:
                    item.origin_move_id.cancel_invoice_bkav()
                    item.exists_bkav = True
        return res