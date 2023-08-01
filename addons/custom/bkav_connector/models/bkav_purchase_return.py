# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountMovePurchaseReturn(models.Model):
    _inherit = 'account.move'


    def get_bkav_data_pr(self):
        bkav_data = []
        for invoice in self:            
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            exchange_rate = invoice.exchange_rate or 1.0
            for line in invoice.invoice_line_ids:
                item_name = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else ''
                vat = 0
                if line.tax_ids:
                    vat = line.tax_ids[0].amount                                                                                                                                                                                
                item = {
                    "ItemName": item_name,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": abs(line.quantity) or 0.0,
                    "Price": abs(line.price_unit) * exchange_rate,
                    "Amount": abs(line.price_subtotal) * exchange_rate,
                    "TaxAmount": abs((line.tax_amount or 0.0)) * exchange_rate,
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": abs(line.price_subtotal * line.discount/100) * exchange_rate,
                    "IsDiscount": 1 if line.discount != 0 else 0
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
                    raise ValidationError('Không có tác vụ điều chỉnh hóa đơn NCC. Vui lòng liên hệ quản trị viên!')
                    # kiểm tra hóa đơn gốc
                    # gốc là out_invoice => điều chỉnh giảm
                    # gốc là out_refund => điều chỉnh tăng
                    # item['IsIncrease'] = 1 if (invoice.move_type == 'in_refund') else 0


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
                    "CurrencyID": invoice.currency_id.name if invoice.currency_id.name else invoice.company_id.currency_id.name,
                    "ExchangeRate": exchange_rate,
                    "InvoiceForm": "",
                    "InvoiceSerial": invoice.invoice_serial if invoice.invoice_serial else "",
                    "InvoiceNo": invoice.invoice_no if invoice.invoice_no else 0,
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data