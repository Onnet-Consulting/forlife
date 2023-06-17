# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time
import logging
import gzip
import base64
import json
import requests
from Crypto.Cipher import AES

_logger = logging.getLogger(__name__)

disable_create_function = False


def connect_bkav(data, configs):
    # Compress the data using gzip
    compressed_data = gzip.compress(str(data).encode("utf-8"))

    # Decode the partner token
    partner_token = configs.get('partner_token')
    encryption_key, iv = partner_token.split(":")
    encryption_key = base64.b64decode(encryption_key)
    iv = base64.b64decode(iv)

    # Create a padding function to ensure data is padded to a 16 byte boundary
    def pad(data):
        pad_length = 16 - (len(data) % 16)
        return data + bytes([pad_length] * pad_length)

    # Pad the compressed data to a 16 byte boundary
    padded_compressed_data = pad(compressed_data)

    # Create an AES cipher object using the encryption key and CBC mode
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)

    # Encrypt the padded compressed data
    encrypted_data = cipher.encrypt(padded_compressed_data)

    # Base64 encode the encrypted data
    encrypted_data = base64.b64encode(encrypted_data).decode("utf-8")

    def get_proxies():
        http_proxy = "http://10.207.210.3:3128"
        https_proxy = "https://10.207.210.3:3128"
        ftp_proxy = "ftp://10.207.210.3:3128"

        proxies = {
            "http": http_proxy,
            "https": https_proxy,
            "ftp": ftp_proxy
        }
        return proxies

    headers = {
        "Content-Type": "text/xml",
        "SOAPAction": "http://tempuri.org/ExecCommand"
    }

    soap_request = f"""
                <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <ExecCommand xmlns="http://tempuri.org/">
                          <partnerGUID>{configs.get('partner_guid')}</partnerGUID>
                          <CommandData>{encrypted_data}</CommandData>
                      </ExecCommand>
                   </soapenv:Body>
                </soapenv:Envelope>
            """
    proxies = get_proxies()

    response = requests.post(configs.get('bkav_url'), headers=headers, data=soap_request, timeout=3.5)

    mes = response.content.decode("utf-8")

    start_index = mes.index("<ExecCommandResult>") + len("<ExecCommandResult>")
    end_index = mes.index("</ExecCommandResult>")
    res = response.content[start_index:end_index]

    decoded_string = base64.b64decode(res)
    cipher2 = AES.new(encryption_key, AES.MODE_CBC, iv)
    plaintext = cipher2.decrypt(decoded_string)
    plaintext = plaintext.rstrip(plaintext[-4:])
    try:
        decode = gzip.decompress(plaintext).decode()
    except Exception as ex:
        _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
        return False
    response_bkav = json.loads(decode)

    if response_bkav['Status'] == 0:
        if type(response_bkav['Object']) == int:
            return response_bkav['Object']
        elif type(response_bkav['Object']) == str and len(response_bkav['Object']) == 0:
            return response_bkav['Object']
        else:
            status_index = response_bkav['Object'].index('"Status":') + len('"Status":')
            mes_index_s = response_bkav['Object'].index('"MessLog":"') + len('"MessLog":"')
            mes_index_e = response_bkav['Object'].index('"}]')
            response_status = response_bkav['Object'][status_index]
            response_mes = response_bkav['Object'][mes_index_s:mes_index_e]
            invoice_guid = (json.loads(response_bkav['Object']))[0]["InvoiceGUID"]
            invoice_no = (json.loads(response_bkav['Object']))[0]["InvoiceNo"]
    else:
        response_status = '1'
        response_mes = response_bkav['Object']
        invoice_guid = ''
        invoice_no = ''

    return {
        'status': response_status,
        'message': response_mes,
        'invoice_guid': invoice_guid,
        'invoice_no': invoice_no,
    }


class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    exists_bkav = fields.Boolean(default=False, copy=False)
    is_post_bkav = fields.Boolean(default=False, string="Có tạo hóa đơn BKAV ngay?", copy=False)
    company_type = fields.Selection(related="partner_id.company_type")
    sequence = fields.Integer(string='Sequence',
                              default=lambda self: self.env['ir.sequence'].next_by_code('account.move.sequence'))

    is_check_cancel = fields.Boolean(default=False, copy=False)

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status_get_values', store=1, copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_e_date = fields.Char('Ngày HDDT', copy=False)

    data_status = fields.Char('')
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
                                            ('15', 'Điều chỉnh chiết khấu')])

    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)

    def get_bkav_config(self):
        return {
            'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
            'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
            'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
            'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
            'cmd_addInvoiceEdit': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit'),
            'cmd_addInvoiceEditDiscount': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit_discount'),
            'cmd_addInvoiceReplace': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_replace'),
            'cmd_updateInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.update_einvoice'),
            'cmd_deleteInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.delete_einvoice'),
            'cmd_cancelInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.cancel_einvoice'),
            'cmd_getInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_einvoice'),
            'cmd_getStatusInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_status_einvoice'),
            'cmd_downloadPDF': self.env['ir.config_parameter'].sudo().get_param('bkav.download_pdf'),
            'cmd_downloadXML': self.env['ir.config_parameter'].sudo().get_param('bkav.download_xml')
        }

    def download_e_invoice(self):
        if self.eivoice_file:
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                       % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'self',
            }
        else:
            raise ValidationError(_("Don't have any eInvoice in this invoice. Please check again!"))

    def preview_e_invoice(self):
        if self.eivoice_file:
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s"
                       % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'new',
            }
        else:
            raise ValidationError(_("Don't have any eInvoice in this invoice. Please check again!"))

    def create_invoice_bkav(self):
        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": int(configs.get('cmd_addInvoice')),
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceTypeID": 10,
                        "InvoiceDate": self.invoice_date.isoformat() if self.invoice_date else '',
                        "BuyerName": self.partner_id.name if self.partner_id.name else '',
                        "BuyerTaxCode": self.partner_id.vat if self.partner_id.vat else '',
                        "BuyerUnitName": self.partner_id.name if self.partner_id.name else '',
                        "BuyerAddress": self.partner_id.country_id.name if self.partner_id.country_id.name else '',
                        "BuyerBankAccount": self.partner_bank_id.id if self.partner_bank_id.id else '',
                        "PayMethodID": 1,
                        "ReceiveTypeID": 3,
                        "ReceiverEmail": self.company_id.email if self.company_id.email else '',
                        "ReceiverMobile": self.company_id.mobile if self.company_id.mobile else '',
                        "ReceiverAddress": self.company_id.street if self.company_id.street else '',
                        "ReceiverName": self.company_id.name if self.company_id.name else '',
                        "Note": "Hóa đơn mới tạo",
                        "BillCode": "",
                        "CurrencyID": self.company_id.currency_id.name if self.company_id.currency_id.name else '',
                        "ExchangeRate": 1.0,
                        "InvoiceForm": "",
                        "InvoiceSerial": "",
                        "InvoiceNo": 0,
                        "OriginalInvoiceIdentify": "[C23TAA/001]_[TM]_[0000001]",
                    },
                    "ListInvoiceDetailsWS": [
                        {
                            "ItemName": (line.product_id.name or line.name) if (line.product_id.name or line.name) else '',
                            "UnitName": line.product_uom_id.name or '',
                            "Qty": line.quantity or 0.0,
                            "Price": line.price_unit,
                            "Amount": line.price_subtotal,
                            "TaxRateID": 3,
                            "TaxRate": 10,
                            "TaxAmount": line.tax_amount or 0.0,
                            "ItemTypeID": 0
                        }
                        for line in self.invoice_line_ids],
                    "ListInvoiceAttachFileWS": [
                        {
                            "FileName": "Test",
                            "FileExtension": "docx",
                            "FileContent": ""
                        },
                        {
                            "FileName": "Test",
                            "FileExtension": "docx",
                            "FileContent": ""
                        }
                    ],
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
            return False
        if response.get('status') == '1':
            try:
                self.message_post(body=(response.get('message')))
            except Exception as ex:
                _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                return False
        else:
            self.message_post(body=_('Đã tạo thành công hóa đơn trên BKAV!!'))
            self.exists_bkav = True
            self.invoice_guid = response.get('invoice_guid')
            self.invoice_no = response.get('invoice_no')
            self.getting_invoice_status()

    def update_invoice_bkav(self):
        data = {
            "CmdType": 200,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceTypeID": 10,
                        "InvoiceDate": self.invoice_date.isoformat() if self.invoice_date else '',
                        "BuyerName": self.partner_id.name if self.partner_id.name else '',
                        "BuyerTaxCode": self.partner_id.vat if self.partner_id.vat else '',
                        "BuyerUnitName": self.partner_id.name if self.partner_id.name else '',
                        "BuyerAddress": self.partner_id.country_id.name if self.partner_id.country_id.name else '',
                        "BuyerBankAccount": self.partner_bank_id.id if self.partner_bank_id.id else '',
                        "PayMethodID": 1,
                        "ReceiveTypeID": 3,
                        "ReceiverEmail": self.company_id.email if self.company_id.email else '',
                        "ReceiverMobile": self.company_id.mobile if self.company_id.mobile else '',
                        "ReceiverAddress": self.company_id.street if self.company_id.street else '',
                        "ReceiverName": self.company_id.name if self.company_id.name else '',
                        "Note": "Hóa đơn được cập nhật",
                        "BillCode": "",
                        "CurrencyID": self.company_id.currency_id.name if self.company_id.currency_id.name else '',
                        "ExchangeRate": 1.0,
                        "InvoiceForm": "",
                        "InvoiceSerial": "",
                        "InvoiceNo": 0,
                        "OriginalInvoiceIdentify": "[C23TAA/001]_[TM]_[0000001]",
                        "InvoiceGUID": self.invoice_guid,
                    },
                    "ListInvoiceDetailsWS": [
                        {
                            "ItemName": line.product_id.name or '',
                            "UnitName": line.uom_id.name or '',
                            "Qty": line.quantity or 0.0,
                            "Price": line.price_unit or 0.0,
                            "Amount": line.price_subtotal or 0.0,
                            "TaxRateID": 3,
                            "TaxRate": 10,
                            "TaxAmount": line.tax_amount or 0.0,
                            "ItemTypeID": 0
                        }
                        for line in self.invoice_line_ids],
                    "ListInvoiceAttachFileWS": [
                        {
                            "FileName": "Test",
                            "FileExtension": "docx",
                            "FileContent": ""
                        },
                        {
                            "FileName": "Test",
                            "FileExtension": "docx",
                            "FileContent": ""
                        }
                    ],
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        configs = self.get_bkav_config()
        response = connect_bkav(data, configs)
        if response.get('status') == '1':
            try:
                self.message_post(body=(response.get('message')))
            except Exception as ex:
                _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                return False
        else:
            self.message_post(body=_('Đã cập nhật thành công hóa đơn trên BKAV!!'))

    def action_download_view_e_invoice(self):
        data_action_download = {
            "CmdType": 804,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceGUID": self.invoice_guid,
                    },
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        configs = self.get_bkav_config()
        response_action = connect_bkav(data_action_download, configs)
        if response_action.get('status') == '1':
            try:
                self.message_post(body=(response_action.get('message')))
            except Exception as ex:
                _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                return False
        else:
            self.message_post(body=('Có thể xem preview và tải xuống HĐĐT'))
            url = 'https://wsdemo.ehoadon.vn' + response_action.get('message')
            return {
                'target': 'new',
                'type': 'ir.actions.act_url',
                'url': url + '?download=true',
            }

    def cancel_invoice(self):
        data = {
            "CmdType": 202,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceGUID": self.invoice_guid,
                        "Reason": "Hủy vì sai sót"
                    },
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        configs = self.get_bkav_config()
        response = connect_bkav(data, configs)
        if response.get('status') == '1':
            try:
                self.message_post(body=(response.get('message')))
            except Exception as ex:
                _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                return False
        else:
            self.message_post(body=_('Đã Hủy thành công HĐĐT trên hệ thống BKAV!!'))
            self.is_check_cancel = True
            self.getting_invoice_status()

    def delete_invoice(self):
        data = {
            "CmdType": 301,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceGUID": self.invoice_guid,
                        "Reason": "Xóa vì sai sót"
                    },
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        configs = self.get_bkav_config()
        response = connect_bkav(data, configs)
        if response.get('status') == '1':
            try:
                self.message_post(body=(response.get('message')))
            except Exception as ex:
                _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                return False
        else:
            self.message_post(body=_('Đã Xóa thành công HĐĐT trên hệ thống BKAV!!'))

    def getting_invoice_status(self):
        data = {
            "CmdType": 801,
            "CommandObject": self.invoice_guid,
        }
        response = connect_bkav(data)
        try:
            pass
        except Exception as ex:
            _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
            return False
        self.data_status = response

    def getting_sign_the_bill_hsm(self):
        data = {
            "CmdType": 205,
            "CommandObject": self.invoice_guid,
        }
        configs = self.get_bkav_config()
        response = connect_bkav(data, configs)
        if not self.invoice_line_ids:
            self.message_post(body=('Không thể kí HSM thành công khi hóa đơn không có sản phẩm!!'))
        else:
            self.message_post(body=_('Đã kí HSM thành công HĐĐT trên hệ thống BKAV!!'))
            self.getting_invoice_status()

    def getting_invoice_history(self):
        data = {
            "CmdType": 802,
            "CommandObject": self.invoice_guid,
        }
        configs = self.get_bkav_config()
        response = connect_bkav(data, configs)
        try:
            pass
        except Exception as ex:
            _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
            return False
        self.invoice_e_date = (json.loads(response['Object']))[0]["CreateDate"]

    @api.depends('data_status')
    def _compute_data_compare_status_get_values(self):
        for rec in self:
            for line in self._fields['data_compare_status'].selection:
                if rec.data_status == line[0]:
                    rec.invoice_state_e = line[1]

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.exists_bkav:
                try:
                    self.update_invoice_bkav()
                    self.getting_invoice_status()
                except Exception as ex:
                    _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                    return False
            else:
                if rec.is_post_bkav:
                    try:
                        self.create_invoice_bkav()
                        self.getting_invoice_status()
                    except Exception as ex:
                        _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
                        return False
                else:
                    pass
        return res

    def post_invoice_to_bkav_end_day(self):
        today = datetime.now().date()
        next_day = today + timedelta(days=1)
        start_of_day = datetime.combine(next_day, time(hour=2, minute=0, second=0))
        end_of_day = datetime.combine(today, time.max)
        invoices = self.search(
            [('is_post_bkav', '=', False), ('state', '=', 'posted'),
             ('create_date', '>=', start_of_day), ('create_date', '<=', end_of_day)])
        if len(invoices):
            inv_bkav = self.create({
                'partner_id': self.env.ref('base.partner_admin').id,
                'invoice_date': today,
                'is_post_bkav': True,
                'invoice_description': f"Hóa đơn bán lẻ cuối ngày {today.strftime('%Y/%m/%d')}",
                'invoice_line_ids': [(0, 0, line.copy_data()[0]) for line in invoices.mapped('invoice_line_ids')]
            })
            inv_bkav.action_post()
