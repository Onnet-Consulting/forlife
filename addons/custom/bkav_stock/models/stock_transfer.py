# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import json
from ...bkav_connector.models import bkav_action


class StockTransfer(models.Model):
    _inherit = 'stock.transfer'

    vendor_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng kinh tế số")
    delivery_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng số")
    location_name = fields.Char('Tên kho xuất')
    location_dest_name = fields.Char('Tên kho nhập')
    transporter_id = fields.Many2one('res.partner', string="Người/Đơn vị vận chuyển")

    @api.onchange('delivery_contract_id')
    def _onchange_delivery_contract(self):
        if self.delivery_contract_id:
            self.transporter_id = self.delivery_contract_id.vendor_id.id

    @api.onchange('location_id','location_dest_id')
    def _onchange_name_location(self):
        if self.location_id:
            self.location_name = self.location_id.location_id.name+'/'+self.location_id.name
        if self.location_dest_id:
            self.location_dest_name = self.location_dest_id.location_id.name+'/'+self.location_dest_id.name

    #bkav
    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, string="Đã ký HĐ trên BKAV", copy=False)
    is_check_cancel = fields.Boolean(default=False, copy=False, string="Đã hủy")
    is_general = fields.Boolean(default=False, copy=False, string="Đã chạy tổng hợp cuối ngày")

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=1,copy=False)
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
    

    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            InvoiceTypeID = 5
            ShiftCommandNo = invoice.name
            if invoice.location_dest_id.id_deposit or invoice.location_id.id_deposit:
                InvoiceTypeID = 6
                ShiftCommandNo = invoice.vendor_contract_id.name if invoice.vendor_contract_id else ''
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            sequence = 0
            for line in invoice.stock_transfer_line:
                sequence += 1
                item = {
                    "ItemName": line.product_id.name or '',
                    "UnitName": line.uom_id.name or '',
                    "Qty": line.qty_out or 0.0,
                    "Price": 0.0,
                    "Amount": 0.0,
                    "TaxAmount": 0.0,
                    "ItemTypeID": 0.0,
                    "IsDiscount": 0
                }
                list_invoice_detail.append(item)
            company_id = invoice.company_id
            partner_id = invoice.company_id.partner_id
            uidefind = {
                        "ShiftCommandNo": ShiftCommandNo,
                        "ShiftCommandDate": invoice.date_transfer.strftime('%Y-%m-%d'),
                        "ShiftUnitName": company_id.name if company_id.name else '',
                        "ShiftReason": invoice.note if invoice.note else '',
                        "ReferenceNote": 'Điều chuyển hàng hóa, nguyên vật liệu.',
                        "TransporterName": invoice.transporter_id.name if invoice.transporter_id else '',
                        "ContractNo": invoice.delivery_contract_id.name if invoice.delivery_contract_id else '',
                        "OutWareHouse": invoice.location_name if invoice.location_name else invoice.location_id.location_id.name+'/'+invoice.location_id.name,
                        "InWareHouse": invoice.location_dest_name if invoice.location_dest_name else invoice.location_dest_id.location_id.name+'/'+invoice.location_dest_id.name,
                        "Transportation": 'Ô tô/Xe máy',
                    }
            if invoice.location_dest_id.id_deposit or invoice.location_id.id_deposit:
                check_lc_id = invoice.location_dest_id if invoice.location_dest_id.id_deposit else invoice.location_id
                location_get_tax_id = self.env['stock.location'].sudo().search([('code','=',check_lc_id.code),('company_id','!=', company_id.id)],limit=1).sudo()
                uidefind.update({
                    "TaxCodeAgent": location_get_tax_id.sudo().company_id.vat if location_get_tax_id.sudo() and location_get_tax_id.sudo().company_id else '',
                    "ReferenceNote": location_get_tax_id.sudo().company_id.name,
                })
                partner_id = location_get_tax_id.sudo().company_id.partner_id
            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": InvoiceTypeID,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": partner_id.name if partner_id.name else '',
                    "BuyerTaxCode": partner_id.vat if partner_id.vat else '',
                    "BuyerUnitName": partner_id.name if partner_id.name else '',
                    "BuyerAddress": partner_id.country_id.name if partner_id.country_id.name else '',
                    "BuyerBankAccount": '',
                    "PayMethodID": 20,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": company_id.email if company_id.email else '',
                    "ReceiverMobile": company_id.mobile if company_id.mobile else '',
                    "ReceiverAddress": company_id.street if company_id.street else '',
                    "ReceiverName": company_id.name if company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": company_id.currency_id.name if company_id.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    # "OriginalInvoiceIdentify": '',  # dùng cho hóa đơn điều chỉnh
                    "UIDefine": json.dumps(uidefind),
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": invoice.name,
                "ListInvoiceDetailsWS": list_invoice_detail,
                "ListInvoiceAttachFileWS": [],
            })
        return bkav_data
        
    def _check_info_before_bkav(self):
        if self.is_general:
            return False
        if self.location_dest_id.id_deposit and self.location_id.id_deposit:
            return False
        return True

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
        data = self.get_bkav_data()
        return bkav_action.create_invoice_bkav(self,data)

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
        return bkav_action.cancel_invoice_bkav(self)

    def delete_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.delete_invoice_bkav(self)

    def download_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.download_invoice_bkav(self)


    def action_cancel(self):
        res = super(StockTransfer, self).action_cancel()
        self.cancel_invoice_bkav()
        return res
    
    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(StockTransfer, self).unlink()