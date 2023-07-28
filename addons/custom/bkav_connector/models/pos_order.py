# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from . import bkav_action

class AccountMovePosOrder(models.Model):
    _inherit = 'account.move'


    def get_bkav_data_pos(self):
        bkav_data = []
        for invoice in self:
            pos_order_id = invoice.pos_order_id
            if not pos_order_id or invoice.move_type not in ('out_invoice', 'out_refund'):
                continue           
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            for line in pos_order_id.lines:
                #SP Voucher k đẩy BKAV
                # if line.product_id.voucher:continue
                vat = 0
                if line.tax_ids:
                    vat = line.tax_ids[0].amount
                item = {
                    "ItemName": line.product_id.name,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.qty,
                    "Price": line.price_subtotal/ line.qty,
                    "Amount": line.price_subtotal,
                    "TaxAmount": (line.price_subtotal_incl - line.price_subtotal or 0.0),
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": line.price_subtotal * line.discount/100,
                    "IsDiscount": 1 if line.is_promotion else 0
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
                    item['IsIncrease'] = 1 if (invoice.origin_move_id.move_type == 'out_invoice') else 0
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
                    "PayMethodID": 7,
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
        res = super(AccountMovePosOrder, self)._post()
        for invoice in self:
            pos_order_id = invoice.pos_order_id
            if not pos_order_id or invoice.move_type not in ('out_invoice', 'out_refund'):
                continue
            if pos_order_id.invoice_info_company_name and pos_order_id.invoice_info_address and pos_order_id.invoice_info_tax_number:
                invoice.create_invoice_bkav()
        return res
    