# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, timedelta
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

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
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

    response = requests.post(configs.get('bkav_url'), headers=headers, data=soap_request, timeout=3.5)

    mes = response.content.decode("utf-8")

    start_index = mes.index("<ExecCommandResult>") + len("<ExecCommandResult>")
    end_index = mes.index("</ExecCommandResult>")
    res = response.content[start_index:end_index]

    decoded_string = base64.b64decode(res)
    cipher2 = AES.new(encryption_key, AES.MODE_CBC, iv)
    plaintext = cipher2.decrypt(decoded_string)
    plaintext = plaintext.rstrip(plaintext[-1:])
    try:
        result_decode = gzip.decompress(plaintext).decode()
    except Exception as ex:
        _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
        raise ValidationError(f'Nhận khách từ lỗi của BKAV {ex}')
    return json.loads(result_decode)
    #
    # if response_bkav['Status'] == 0:
    #     if type(response_bkav['Object']) == int:
    #         return response_bkav['Object']
    #     elif type(response_bkav['Object']) == str and len(response_bkav['Object']) == 0:
    #         return response_bkav['Object']
    #     else:
    #         status_index = response_bkav['Object'].index('"Status":') + len('"Status":')
    #         mes_index_s = response_bkav['Object'].index('"MessLog":"') + len('"MessLog":"')
    #         mes_index_e = response_bkav['Object'].index('"}]')
    #         response_status = response_bkav['Object'][status_index]
    #         if response_status == '1':
    #             response_mes = response_bkav['Object']
    #             invoice_guid = ''
    #             invoice_no = ''
    #         else:
    #             response_mes = response_bkav['Object'][mes_index_s:mes_index_e]
    #             invoice_guid = (json.loads(response_bkav['Object']))[0]["InvoiceGUID"]
    #             invoice_no = (json.loads(response_bkav['Object']))[0]["InvoiceNo"]
    # else:
    #     response_status = '1'
    #     response_mes = response_bkav['Object']
    #     invoice_guid = ''
    #     invoice_no = ''
    #
    # return {
    #     'status': response_status,
    #     'message': response_mes,
    #     'invoice_guid': invoice_guid,
    #     'invoice_no': invoice_no,
    # }


class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    exists_bkav = fields.Boolean(default=False, copy=False)
    is_post_bkav = fields.Boolean(default=False, string="Đã tạo HĐ trên BKAV", copy=False)
    company_type = fields.Selection(related="partner_id.company_type")
    sequence = fields.Integer(string='Sequence',
                              default=lambda self: self.env['ir.sequence'].next_by_code('account.move.sequence'))

    is_check_cancel = fields.Boolean(default=False, copy=False)

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status_get_values', store=1,
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
    origin_move_id = fields.Many2one('account.move', 'Hóa đơn gốc', domain=[('move_type', '=', 'out_invoice')])
    issue_invoice_type = fields.Selection([
        ('vat', 'GTGT'),
        ('adjust', 'Điều chỉnh'),
        ('replace', 'Thay thế')
    ], 'Loại phát hành', default='vat', required=True)

    @api.depends('data_compare_status')
    def _compute_data_compare_status_get_values(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def get_invoice_identify(self):
        invoice_form = self.invoice_form or ''
        invoice_serial = self.invoice_serial or ''
        invoice_no = self.invoice_no or ''
        return f"[{invoice_form}]_[{invoice_serial}]_[{invoice_no}]"

    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.invoice_date, datetime.now().time())) if invoice.invoice_date else fields.Datetime.context_timestamp(invoice, datetime.now())
            list_invoice_detail = []
            sign = 1 if invoice.move_type in ('out_invoice', 'in_invoice') else -1
            for line in invoice.invoice_line_ids:
                item_name = (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else ''
                item = {
                    "ItemName": item_name if not line.promotions else item_name + " (Hàng tặng không thu tiền)",
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": (line.price_unit - line.price_unit * line.discount / 100) * sign,
                    "Amount": line.price_total * sign,
                    # "TaxRateID": 3,
                    # "TaxRate": 10,
                    "TaxAmount": (line.tax_amount or 0.0) * sign,
                    "ItemTypeID": 0,
                    "IsDiscount": 1 if line.promotions else 0
                }
                if line.tax_ids:
                    if line.tax_ids[0].amount == 0:
                        tax_rate_id = 0
                    elif line.tax_ids[0].amount == 5:
                        tax_rate_id = 1
                    elif line.tax_ids[0].amount == 10:
                        tax_rate_id = 3
                    else:
                        tax_rate_id = 6
                    item.update({
                        "TaxRateID": tax_rate_id,
                        "TaxRate": line.tax_ids[0].amount
                    })
                if invoice.issue_invoice_type == 'edit':
                    # kiểm tra hóa đơn gốc
                    # gốc là out_invoice => điều chỉnh giảm
                    # gốc là out_refund => điều chỉnh tăng
                    item['IsIncrease'] = invoice.origin_move_id.move_type != 'out_invoice'

                list_invoice_detail.append(item)
            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerTaxCode": invoice.partner_id.vat if invoice.partner_id.vat else '',
                    "BuyerUnitName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerAddress": invoice.partner_id.country_id.name if invoice.partner_id.country_id.name else '',
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

    def get_bkav_config(self):
        return {
            'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
            'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
            'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
            'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
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

    def create_invoice_bkav(self):
        # validate với trường hợp điều chỉnh thay thế
        if self.issue_invoice_type in ('edit', 'replace') and not self.origin_move_id.invoice_no:
            raise ValidationError('Vui lòng chọn hóa đơn gốc cho đã được phát hành để điều chỉnh hoặc thay thế')

        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": int(configs.get('cmd_addInvoice')),
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
                    'invoice_e_date': datetime.strptime(result_data.get('SignedDate').split('.')[0], '%Y-%m-%dT%H:%M:%S.%f') - timedelta(
                        hours=7) if result_data.get('SignedDate') else None
                })
                self.getting_invoice_status()
            except:
                self.get_invoice_bkav()

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

    def get_invoice_bkav(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_getInvoice')),
            "CommandObject": self.id
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
                'invoice_e_date': datetime.strptime(result_data.get('SignedDate').split('.')[0], '%Y-%m-%dT%H:%M:%S.%f') - timedelta(
                    hours=7) if result_data.get('SignedDate') else None,
                'invoice_state_e': str(result_data.get('InvoiceStatusID'))
            })

    def cancel_invoice(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_cancelInvoice')),
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
        _logger.info(f'BKAV - data cancel invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))
        else:
            self.is_check_cancel = True
            self.getting_invoice_status()

    # def button_cancel(self):
    #     res = super(AccountMoveBKAV, self).button_cancel()
    #     self.cancel_invoice()
    #     return res

    def delete_invoice(self):
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_deleteInvoice')),
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
        _logger.info(f'BKAV - data delete invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))

    def action_download_view_e_invoice(self):
        if not self.eivoice_file:
            configs = self.get_bkav_config()
            data = {
                "CmdType": int(configs.get('cmd_downloadPDF')),
                "CommandObject": self.id,
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
    #
    # def getting_invoice_history(self):
    #     data = {
    #         "CmdType": 802,
    #         "CommandObject": self.invoice_guid,
    #     }
    #     configs = self.get_bkav_config()
    #     response = connect_bkav(data, configs)
    #     try:
    #         pass
    #     except Exception as ex:
    #         _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
    #         return False
    #     self.invoice_e_date = (json.loads(response['Object']))[0]["CreateDate"]

    # def action_post(self):
    #     res = super().action_post()
    #     for rec in self:
    #         if rec.exists_bkav:
    #             try:
    #                 self.update_invoice_bkav()
    #                 self.getting_invoice_status()
    #             except Exception as ex:
    #                 _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
    #                 return False
    #         else:
    #             if rec.is_post_bkav:
    #                 try:
    #                     self.create_invoice_bkav()
    #                     self.getting_invoice_status()
    #                 except Exception as ex:
    #                     _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
    #                     return False
    #             else:
    #                 pass
    #     return res

    # def post_invoice_to_bkav_end_day(self):
    #     today = datetime.now().date()
    #     next_day = today + timedelta(days=1)
    #     start_of_day = datetime.combine(next_day, time(hour=2, minute=0, second=0))
    #     end_of_day = datetime.combine(today, time.max)
    #     invoices = self.search(
    #         [('is_post_bkav', '=', False), ('state', '=', 'posted'),
    #          ('create_date', '>=', start_of_day), ('create_date', '<=', end_of_day)])
    #     if len(invoices):
    #         inv_bkav = self.create({
    #             'partner_id': self.env.ref('base.partner_admin').id,
    #             'invoice_date': today,
    #             'is_post_bkav': True,
    #             'invoice_description': f"Hóa đơn bán lẻ cuối ngày {today.strftime('%Y/%m/%d')}",
    #             'invoice_line_ids': [(0, 0, line.copy_data()[0]) for line in invoices.mapped('invoice_line_ids')]
    #         })
    #         inv_bkav.action_post()
