# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountMoveSaleOrder(models.Model):
    _inherit = 'account.move'

    def _get_promotion_in_sale(self):
        list_invoice_detail = []
        vip_amount = {}
        reward_amount = {}
        for promotion_id in self.promotion_ids:
            if promotion_id.promotion_type == 'vip_amount':
                vat = 0
                if promotion_id.product_id.taxes_id:
                    vat = promotion_id.product_id.taxes_id[0].amount
                if vat not in list(vip_amount.keys()):
                    vip_amount.update({
                        vat:promotion_id.value,
                    })
                else:
                    vip_amount[vat] += promotion_id.value
            if promotion_id.promotion_type == 'reward':
                vat = 0
                if promotion_id.product_id.taxes_id:
                    vat = promotion_id.product_id.taxes_id[0].amount
                if vat not in list(reward_amount.keys()):
                    reward_amount.update({
                        vat:promotion_id.value,
                    })
                else:
                    reward_amount[vat] += promotion_id.value
        for vat, value in vip_amount.items():
            value_not_tax = abs(value)/(1+vat/100)
            item = {
                "ItemName": 'Chiết khấu hạng thẻ',
                "UnitName": '',
                "Qty": 1.0,
                "Price": value_not_tax,
                "Amount": value_not_tax,
                "TaxAmount": value - value_not_tax,
                "ItemTypeID": 0,
                "IsDiscount": 1,
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
            list_invoice_detail.append(item)
        
        for vat, value in reward_amount.items():
            value_not_tax = abs(value)/(1+vat/100)
            item = {
                "ItemName": 'Chiết khấu tổng đơn',
                "UnitName": '',
                "Qty": 1.0,
                "Price": value_not_tax,
                "Amount": value_not_tax,
                "TaxAmount": value - value_not_tax,
                "ItemTypeID": 0,
                "IsDiscount": 1,
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
            list_invoice_detail.append(item)
        return list_invoice_detail


    def get_bkav_data_so(self):
        bkav_data = []
        for invoice in self:
            
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            for line in invoice.invoice_line_ids:
                #SP Voucher k đẩy BKAV
                if line.product_id.voucher:continue
                ItemName = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else ''
                if line.sale_line_ids and line.sale_line_ids[0].x_free_good:
                    ItemName += " (Hàng tặng không thu tiền)"
                vat, tax_rate_id = self._get_vat_line_bkav(line)
                Price = round(line.price_unit/ ((1 + vat/100)))
                Amount = Price * line.quantity
                item = {
                    "ItemName": ItemName,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity,
                    "Price": Price,
                    "Amount": Amount,
                    "TaxAmount": line.tax_amount or 0.0,
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": line.price_total * line.discount/100,
                    "IsDiscount": 0
                }
                item.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                if invoice.issue_invoice_type == 'adjust':
                    item['IsIncrease'] = 1 if (invoice.move_type == 'out_invoice') else 0

                list_invoice_detail.append(item)

            list_invoice_detail.extend(self._get_promotion_in_sale())

            BuyerName = invoice.partner_id.name if invoice.partner_id.name else ''

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
                    "InvoiceSerial": invoice.invoice_serial if invoice.invoice_serial else "",
                    "InvoiceNo": invoice.invoice_no if invoice.invoice_no else 0,
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data
    

    # def _post(self, soft=True):
    #     res = super(AccountMoveSaleOrder, self)._post(soft)
    #     for item in self:
    #         if item.issue_invoice_type == 'adjust':
    #             if not item.origin_move_id or not item.origin_move_id.invoice_no:
    #                 raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh')
    #             if item.origin_move_id.amount_total == item.amount_total:
    #                 item.origin_move_id.cancel_invoice_bkav()
    #                 item.exists_bkav = True
    #     return res

# class StockPicking(models.Model):
#     _inherit = 'stock.picking'

#     def create_invoice_out_refund(self):
#         invoice_id = super(StockPicking, self).create_invoice_out_refund()
#         move_id = self.env['account.move'].browse(invoice_id)
#         move_id.update({
#             'origin_move_id': move_id.id,
#             'issue_invoice_type': 'adjust',
#         })