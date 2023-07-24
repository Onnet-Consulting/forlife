# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
import json
from ...bkav_connector.models import bkav_action

class TransferNotExistsBkav(models.Model):
    _name = 'transfer.not.exists.bkav'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'General Transfer Not Exists Bkav'
    _rec_name = 'id'
    _order = 'id desc'

    #bkav
    exists_bkav = fields.Boolean(default=False, copy=False)
    is_post_bkav = fields.Boolean(default=False, string="Đã tạo HĐ trên BKAV", copy=False)
    is_check_cancel = fields.Boolean(default=False, copy=False)

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=1,copy=False)
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

    code = fields.Char(string="Mã", default="New", copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', related='location_id.company_id', store=True)
    date_transfer = fields.Date("Ngày xác nhận xuất", default=lambda x: fields.Date.today(), copy=False)
    location_id = fields.Many2one('stock.location', string="Kho xuất")
    location_dest_id = fields.Many2one('stock.location', string="Kho nhập")
    vendor_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng kinh tế số")
    delivery_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng số")
    location_name = fields.Char('Tên kho xuất')
    location_dest_name = fields.Char('Tên kho nhập')
    transporter_id = fields.Many2one('res.partner', string="Người/Đơn vị vận chuyển")
    transfer_ids = fields.Many2many('stock.transfer', 'stock_transfer_bkav_not_exist', 'bkav_not_exist_id','transfer_id',copy=False, string='DS điều chuyển')
    line_ids = fields.One2many(
        comodel_name='transfer.not.exists.bkav.line',
        inverse_name='parent_id',
        string='DS sản phẩm'
    )
    state = fields.Selection([('new', 'Mới'),('post', 'Đã tích hợp')], copy=False)

    def genarate_code(self):
        location_code = self.location_id.code
        code = 'PTH' + (location_code if location_code else '') + datetime.now().strftime("%y")
        param_code = code+'%'
        query = """ 
            SELECT code
            FROM (
                (SELECT '000001' as code)
                UNION ALL
                (SELECT RIGHT(code,6) as code
                FROM transfer_not_exists_bkav
                WHERE code like %s
                ORDER BY code desc
                LIMIT 1)) as compu
            ORDER BY code desc LIMIT 1
        """
        self._cr.execute(query, (param_code,))
        result = self._cr.fetchall()
        for list_code in result:
            if list_code[0] == '000001':
                code+='000001'
            else:
                code_int = int(list_code[0])
                code+='0'*len(6-len(code_int+1))+str(code_int+1)
        self.code = code

    def general_transfer_not_exists_bkav(self):
        date_now = datetime.utcnow().date()
        # tổng hợp điều chuyển chưa xuat hd
        query = """
            INSERT INTO transfer_not_exists_bkav(location_id, location_dest_id, company_id,
                            location_name, location_dest_name, date_transfer, state)
            SELECT s.location_id, s.location_dest_id, s.company_id, 
                knc.name||'/'||kn.name, kdc.name||'/'||kd.name, 
                (SELECT CURRENT_DATE), 'new'
            FROM stock_transfer s
            JOIN stock_location kn ON s.location_id = kn.id
            JOIN stock_location knc ON kn.location_id = knc.id
            JOIN stock_location kd ON s.location_dest_id = kd.id
            JOIN stock_location kdc ON kd.location_id = kdc.id
            WHERE s.exists_bkav = 'f' 
            AND (s.date_transfer + interval '7 hours')::date < %s
            AND s.state in ('out_approve','in_approve','done')
            AND (kn.id_deposit != 't' or kd.id_deposit != 't')
            GROUP BY s.location_id,s.location_dest_id,s.company_id,knc.name,kn.name,kdc.name,kd.name; 

            INSERT INTO transfer_not_exists_bkav_line(parent_id, product_id, uom_id, quantity)
            (SELECT a.id, b.product_id, b.uom_id, b.quantity
            FROM 
                (SELECT * 
                FROM transfer_not_exists_bkav 
                WHERE state = 'new') as a
            JOIN
                (SELECT s.location_id, s.location_dest_id, l.product_id, l.uom_id, sum(qty_out) as quantity
                FROM stock_transfer s, stock_transfer_line l
                WHERE l.stock_transfer_id = s.id
                AND s.exists_bkav = 'f' 
                AND (s.date_transfer + interval '7 hours')::date < %s
                AND s.state in ('out_approve','in_approve','done')
                GROUP BY s.location_id, s.location_dest_id, l.product_id, l.uom_id) as b 
            ON a.location_id = b.location_id AND a.location_dest_id = b.location_dest_id
            );

            INSERT INTO stock_transfer_bkav_not_exist(bkav_not_exist_id, transfer_id)
            (SELECT a.id, b.id
            FROM 
                (SELECT *
                FROM transfer_not_exists_bkav 
                WHERE state = 'new') as a
            JOIN
                (SELECT s.id, s.location_id, s.location_dest_id
                FROM stock_transfer s
                WHERE s.exists_bkav = 'f' 
                AND (s.date_transfer + interval '7 hours')::date < %s
                AND s.state in ('out_approve','in_approve','done')
                ) as b 
            ON a.location_id = b.location_id AND a.location_dest_id = b.location_dest_id
            );

            UPDATE transfer_not_exists_bkav t SET vendor_contract_id = p.vendor_contract_id
            FROM 
                (SELECT b.id, c.vendor_contract_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.vendor_contract_id is not null) p 
            WHERE t.id = p.id;

            UPDATE transfer_not_exists_bkav t SET delivery_contract_id = p.delivery_contract_id
            FROM 
                (SELECT b.id, c.delivery_contract_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.delivery_contract_id is not null) p 
            WHERE t.id = p.id;

            UPDATE transfer_not_exists_bkav t SET transporter_id = p.transporter_id
            FROM 
                (SELECT b.id, c.transporter_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.transporter_id is not null) p 
            WHERE t.id = p.id;
        """
        self._cr.execute(query, (date_now,date_now,date_now))
        transfer_ids = self.env['transfer.not.exists.bkav'].search([('state','=','new')],order='id asc')
        for transfer_id in transfer_ids:
            transfer_id = transfer_id.sudo().with_company(transfer_id.location_id.company_id)
            transfer_id.genarate_code()
            transfer_id.create_invoice_bkav()
            transfer_id._update_stock_transfer()

    def _update_stock_transfer(self):
        for transfer_id in self:
            if transfer_id.state == 'new':
                transfer_id.state = 'post'
            for transfer in transfer_id.transfer_ids:
                if not transfer.is_general:
                    transfer.is_general = True
                    transfer.exists_bkav = True

    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            InvoiceTypeID = 5
            ShiftCommandNo = invoice.code
            if invoice.location_dest_id.id_deposit or invoice.location_id.id_deposit:
                InvoiceTypeID = 6
                ShiftCommandNo = invoice.vendor_contract_id.name if invoice.vendor_contract_id else ''
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            sequence = 0
            for line in invoice.line_ids:
                sequence += 1
                item = {
                    "ItemName": line.product_id.name or '',
                    "UnitName": line.uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": 0,
                    "Amount": 0,
                    "TaxAmount": 0,
                    "ItemTypeID": 0,
                    "IsDiscount": 0
                }
                list_invoice_detail.append(item)
            company_id = invoice.company_id
            partner_id = company_id.partner_id
            uidefind = {
                        "ShiftCommandNo": ShiftCommandNo,
                        "ShiftCommandDate": invoice.date_transfer.strftime('%Y-%m-%d'),
                        "ShiftUnitName": company_id.name if company_id.name else '',
                        "ShiftReason": 'Xuất điều chuyển nội bộ',
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
                })
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
                "PartnerInvoiceStringID": invoice.code,
                "ListInvoiceDetailsWS": list_invoice_detail,
                "ListInvoiceAttachFileWS": [],
            })
        return bkav_data
    
    def _check_info_before_bkav(self):
        # if self.is_general:
        #     return False
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
        origin_id = False
        is_publish = True
        return bkav_action.create_invoice_bkav(self,data, is_publish, origin_id)

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
        PartnerInvoiceID = 0,
        PartnerInvoiceStringID = self.code
        return bkav_action.cancel_invoice_bkav(self,PartnerInvoiceID,PartnerInvoiceStringID)

    def delete_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        PartnerInvoiceID = 0,
        PartnerInvoiceStringID = self.code
        return bkav_action.delete_invoice_bkav(self,PartnerInvoiceID,PartnerInvoiceStringID)

    def download_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.download_invoice_bkav(self)
    
    
    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(TransferNotExistsBkav, self).unlink()
    
        

class TransferNotExistsBkavLine(models.Model):
    _name = 'transfer.not.exists.bkav.line'

    parent_id = fields.Many2one('transfer.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')

