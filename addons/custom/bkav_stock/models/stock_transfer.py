# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging
import json
_logger = logging.getLogger(__name__)
from ...bkav_connector.models.bkav_connector import connect_bkav


class StockTransfer(models.Model):
    _inherit = 'stock.transfer'

    vendor_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng kinh tế số")
    delivery_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng số")
    location_name = fields.Char('Tên kho xuất')
    location_dest_name = fields.Char('Tên kho nhập')
    transporter_id = fields.Many2one('res.partner', string="Người/Đơn vị vận chuyển")

    @api.onchange('location_id','location_dest_id')
    def _onchange_name_location(self):
        if self.location_id:
            self.location_name = self.location_id.location_id.name+'/'+self.location_id.name
        if self.location_dest_id:
            self.location_dest_name = self.location_dest_id.location_id.name+'/'+self.location_dest_id.name

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
    issue_invoice_type = fields.Selection([
        ('vat', 'GTGT'),
        ('adjust', 'Điều chỉnh'),
        ('replace', 'Thay thế')
    ], 'Loại phát hành', default='vat', required=True)


    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)


    def get_invoice_identify(self):
        invoice_form = self.invoice_form or ''
        invoice_serial = self.invoice_serial or ''
        invoice_no = self.invoice_no or ''
        return f"[{invoice_form}]_[{invoice_serial}]_[{invoice_no}]"
    
    def get_bkav_config(self):
        return {
            'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
            'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
            'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
            'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
            'cmd_addInvoiceStock': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_stock'),
            'cmd_addInvoiceEdit': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit'),
            'cmd_addInvoiceEditDiscount': self.env['ir.config_parameter'].sudo().get_param(
                'bkav.add_einvoice_edit_discount'),
            'cmd_addInvoiceReplace': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_replace'),
            'cmd_updateInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.update_einvoice'),
            'cmd_deleteInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.delete_einvoice'),
            'cmd_cancelInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.cancel_einvoice'),
            'cmd_publishInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.publish_invoice'),
            'cmd_getInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_einvoice'),
            'cmd_getStatusInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_status_einvoice'),
            'cmd_downloadPDF': self.env['ir.config_parameter'].sudo().get_param('bkav.download_pdf'),
            'cmd_downloadXML': self.env['ir.config_parameter'].sudo().get_param('bkav.download_xml')
        }
    

    def getting_invoice_status(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_getStatusInvoice')),
            "CommandObject": self.invoice_guid,
        }
        _logger.info(f'BKAV - data get invoice status to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            self.data_compare_status = str(response.get('Object'))


    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            InvoiceTypeID = 5
            ShiftCommandNo = invoice.name
            if invoice.location_dest_id.id_deposit:
                InvoiceTypeID = 6
                ShiftCommandNo = invoice.vendor_contract_id.name if invoice.vendor_contract_id else ''
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.date_transfer, datetime.now().time())) if invoice.date_transfer else fields.Datetime.context_timestamp(invoice, datetime.now())
            list_invoice_detail = []
            sequence = 0
            for line in invoice.stock_transfer_line:
                sequence += 1
                item = {
                    "ItemName": line.product_id.name or '',
                    "UnitName": line.uom_id.name or '',
                    "Qty": line.qty_out or 0.0,
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
                        "ShiftReason": invoice.note if invoice.note else '',
                        "ReferenceNote": 'Điều chuyển hàng hóa, nguyên vật liệu.',
                        "TransporterName": invoice.transporter_id.name if invoice.transporter_id else '',
                        "ContractNo": invoice.delivery_contract_id.name if invoice.delivery_contract_id else '',
                        "OutWareHouse": invoice.location_name if invoice.location_name else invoice.location_id.location_id.name+'/'+invoice.location_id.name,
                        "InWareHouse": invoice.location_dest_name if invoice.location_dest_name else invoice.location_dest_id.location_id.name+'/'+invoice.location_dest_id.name,
                        "Transportation": 'Ô tô/Xe máy',
                    }
            if invoice.location_dest_id.id_deposit:
                location_get_tax_id = self.env['stock.location'].sudo().search([('code','=',invoice.location_dest_id.code),('company_id','!=', company_id.id)],limit=1).sudo()
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
                "PartnerInvoiceStringID": invoice.name,
                "ListInvoiceDetailsWS": list_invoice_detail,
                "ListInvoiceAttachFileWS": [],
            })
        return bkav_data
    

    def create_invoice_bkav(self):
        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": int(configs.get('cmd_addInvoiceStock')),
            "CommandObject": self.get_bkav_data()
        }
        _logger.info(f'BKAV - data create invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            result_data = json.loads(response.get('Object', []))[0]
            try:
                # ghi dữ liệu
                self.write({
                    'exists_bkav': True,
                    'is_post_bkav': True,
                    'invoice_guid': result_data.get('InvoiceGUID'),
                    'invoice_no': result_data.get('InvoiceNo'),
                    'invoice_form': result_data.get('InvoiceForm'),
                    'invoice_serial': result_data.get('InvoiceSerial'),
                    'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S.%f') if result_data.get('InvoiceDate') else None
                })
                self.getting_invoice_status()
            except:
                self.get_invoice_bkav()


    def get_invoice_bkav(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_getInvoice')),
            "CommandObject": self.invoice_guid
        }
        _logger.info(f'BKAV - data get invoice from BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            result_data = json.loads(response.get('Object', {})).get('Invoice', {})
            self.write({
                'data_compare_status': str(result_data.get('InvoiceStatusID')),
                'exists_bkav': True,
                'is_post_bkav': True,
                'invoice_guid': result_data.get('InvoiceGUID'),
                'invoice_no': result_data.get('InvoiceNo'),
                'invoice_form': result_data.get('InvoiceForm'),
                'invoice_serial': result_data.get('InvoiceSerial'),
                'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S') if result_data.get('InvoiceDate') else None,
                'invoice_state_e': str(result_data.get('InvoiceStatusID'))
            })


    def update_invoice_bkav(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_updateInvoice')),
            "CommandObject": self.get_bkav_data()
        }
        _logger.info(f'BKAV - data update invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))
        else:
            self.getting_invoice_status()


    def publish_invoice_bkav(self):
        configs = self.get_bkav_config()

        data = {
            "CmdType": int(configs.get('cmd_publishInvoice')),
            "CommandObject": self.invoice_guid,
        }
        connect_bkav(data, configs)
        _logger.info(f'BKAV - data publish invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            self.get_invoice_bkav()


    def download_invoice_bkav(self):
        if not self.eivoice_file:
            configs = self.get_bkav_config()
            data = {
                "CmdType": int(configs.get('cmd_downloadPDF')),
                "CommandObject": self.invoice_guid,
            }
            _logger.info(f'BKAV - data download invoice to BKAV: {data}')
            response_action = connect_bkav(data, configs)
            if response_action.get('Status') == '1':
                self.message_post(body=(response_action.get('Object')))
            else:
                attachment_id = self.env['ir.attachment'].sudo().create({
                    'name': f"{self.invoice_no}.pdf",
                    'datas': json.loads(response_action.get('Object')).get('PDF', ''),
                })
                self.eivoice_file = attachment_id
                return {
                    'type': 'ir.actions.act_url',
                    'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                           % (self.eivoice_file.id, self.eivoice_file.name),
                    'target': 'self',
                }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                       % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'self',
            }
