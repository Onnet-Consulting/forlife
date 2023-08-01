# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from . import bkav_action

class AccountMovePosOrder(models.Model):
    _inherit = 'account.move'


    def _get_promotion_in_pos(self, total_point,use_point,rank_total):
        list_invoice = []
        if total_point > 0:
            line_invoice = {
                "ItemName": "Tích điểm",
                "UnitName": 'Đơn vị',
                "Qty": total_point,
                "Price": 0,
                "Amount": 0,
                "TaxAmount": 0,
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
            list_invoice.append(line_invoice)
        if use_point > 0:
            line_invoice = {
                "ItemName": "Tiêu điểm",
                "UnitName": 'Đơn vị',
                "Qty": use_point/1000,
                "Price": 1000,
                "Amount": use_point,
                "TaxAmount": 0,
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
            list_invoice.append(line_invoice)

        if rank_total > 0:
            line_invoice = {
                "ItemName": "Chiết khấu hạng thẻ",
                "UnitName": 'Đơn vị',
                "Qty": 1,
                "Price": rank_total,
                "Amount": rank_total,
                "TaxAmount": 0,
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
            list_invoice.append(line_invoice)

        return list_invoice


    def get_bkav_data_pos(self):
        bkav_data = []
        for invoice in self:
            pos_order_id = invoice.pos_order_id
            if not pos_order_id or invoice.move_type not in ('out_invoice', 'out_refund'):
                continue           
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            total_point = pos_order_id.total_point
            subuse_point = pos_order_id.lines.filtered(
                lambda l: l.is_promotion == True and l.promotion_type == 'point').mapped("subtotal_paid")
            subrank_total = pos_order_id.lines.filtered(
                lambda l: l.is_promotion == True and l.promotion_type == 'card').mapped("subtotal_paid")
            use_point = sum(subuse_point)
            rank_total = sum(subrank_total)
            for line in pos_order_id.lines:
                #SP KM k đẩy BKAV
                if line.is_promotion or line.product_id.voucher or line.product_id.is_product_auto or line.product_id.is_voucher_auto:
                    continue
                vat = 0
                if line.tax_ids:
                    vat = line.tax_ids[0].amount
                itemname = line.product_id.name
                if line.is_reward_line:
                    itemname += '(Hàng tặng khuyến mại không thu tiền)'
                item = {
                    "ItemName": itemname,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.qty,
                    "Price": line.price_bkav,
                    "Amount": line.qty * line.price_bkav,
                    "TaxAmount": (line.price_subtotal_incl - line.price_subtotal or 0.0),
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": line.price_total * line.discount/100,
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
                    item['IsIncrease'] = 1 if (invoice.move_type == 'out_invoice') else 0
                list_invoice_detail.append(item)
            #Them cac SP khuyen mai
            list_invoice_detail.extend(self._get_promotion_in_pos(total_point,use_point,rank_total))

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
                    "InvoiceSerial": invoice.invoice_serial if invoice.invoice_serial else "",
                    "InvoiceNo": invoice.invoice_no if invoice.invoice_no else 0,
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def _post(self, soft=True):
        for invoice in self:
            pos_order_id = invoice.pos_order_id
            if not pos_order_id or invoice.move_type not in ('out_invoice', 'out_refund'):
                continue
            if pos_order_id.invoice_info_company_name and pos_order_id.invoice_info_address and pos_order_id.invoice_info_tax_number:
                if invoice.move_type == 'out_invoice':
                    invoice.create_invoice_bkav()
            if invoice.move_type == 'out_refund':
                if pos_order_id.refunded_order_ids:
                    pos_order_origin_id = pos_order_id.refunded_order_ids[0]
                else: continue
                invoice_origin_id = pos_order_origin_id.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice')[0]
                if not invoice.origin_move_id:
                    invoice.origin_move_id = invoice_origin_id.id
                if not invoice_origin_id.exists_bkav:
                    continue
                if invoice_origin_id.amount_total == invoice.amount_total:
                    invoice_origin_id.cancel_invoice_bkav()
                    invoice_origin_id.exists_bkav = True
                else:
                    invoice.issue_invoice_type = 'adjust'
                    invoice.create_invoice_bkav()
        return super(AccountMovePosOrder, self)._post(soft)
    