from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError

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


class SummaryAccountMovePos(models.Model):
    _inherit = 'summary.account.move.pos'

    def get_bkav_data(self, data, cmd_type=None):
        bkav_data = []
        for invoice in data:
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.invoice_date,
                                                                                       datetime.now().time())) if invoice.invoice_date else fields.Datetime.context_timestamp(
                invoice, datetime.now())
            list_invoice_detail = []
            for line in invoice.line_ids:
                item = {
                    "ItemName": (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else '',
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": line.price_unit * (1 - line.discount / 100),
                    "Amount": line.price_subtotal,
                    "TaxRateID": 3,
                    "TaxRate": 10,
                    "TaxAmount": line.tax_amount or 0.0,
                    "ItemTypeID": 0,
                    # "IsDiscount": 1 if line.promotions else 0
                }
                # if invoice.issue_invoice_type == 'edit':
                    # kiểm tra hóa đơn gốc
                    # gốc là out_invoice => điều chỉnh giảm
                    # gốc là out_refund => điều chỉnh tăng
                #     item['IsIncrease'] = invoice.origin_move_id.move_type != 'out_invoice'
                list_invoice_detail.append(item)
            invoice_json = {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerTaxCode": invoice.partner_id.vat if invoice.partner_id.vat else '',
                    "BuyerUnitName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerAddress": invoice.partner_id.country_id.name if invoice.partner_id.country_id.name else '',
                    "BuyerBankAccount": '321312434535453',
                    "PayMethodID": 1,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": invoice.company_id.email if invoice.company_id.email else '',
                    "ReceiverMobile": invoice.company_id.mobile if invoice.company_id.mobile else '',
                    "ReceiverAddress": invoice.company_id.street if invoice.company_id.street else '',
                    "ReceiverName": invoice.company_id.name if invoice.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": self.env.company.currency_id.name if self.env.company.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    # "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in
                    # ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            }
            if cmd_type == 124:
                invoice_json["Invoice"].update({
                    "Reason": "Huỷ/thay thế/điều chỉnh Hoá đơn với lý do abc",
                    "OriginalInvoiceIdentify": "[1]_[C23TAC]_[153]"
                })
            bkav_data.append(invoice_json)
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
            'cmd_publishInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.publish_einvoice'),
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

    def create_invoice_bkav(self, cmd_type, data_invoice):
        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": cmd_type,
            "CommandObject": data_invoice
        }
        _logger.info(f'BKAV - data create invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            print(response.get('Object'))
        else:
            result_data = json.loads(response.get('Object', []))[0]
            try:
                # ghi dữ liệu
                return {
                    'exists_bkav': True,
                    'is_post_bkav': True,
                    'invoice_guid': result_data.get('InvoiceGUID'),
                    'invoice_no': result_data.get('InvoiceNo'),
                    'invoice_form': result_data.get('InvoiceForm'),
                    'invoice_serial': result_data.get('InvoiceSerial'),
                    'invoice_e_date': datetime.strptime(result_data.get('SignedDate'), '%Y-%m-%dT%H:%M:%S.%f') - timedelta(
                        hours=7) if result_data.get('SignedDate') else None
                }
            except Exception as ex:
                _logger.error(f'BKAV connect_bkav: {ex}')
                return False

    def collect_bills_the_end_day(self):
        synthetic, adjusted = self.get_val_synthetic_account()
        self.summary_post_bkav(synthetic, 101)
        # self.summary_post_bkav(adjusted, 124)

    def summary_post_bkav(self, data, cmd_type=None):
        gui_id_list = []
        for item in data:
            item_bkav = self.get_bkav_data(item, cmd_type)

            einvoice = self.create_invoice_bkav(cmd_type, item_bkav)
            gui_id_list.append(einvoice.get('invoice_guid'))
            item.number_bill = '[{}]_[{}]_[{}]'.format(einvoice.get('invoice_form'),
                                                       einvoice.get('invoice_serial'),
                                                       einvoice.get('invoice_no'))
            item.code = item.number_bill
            item.einvoice_date = einvoice.get('invoice_e_date')
            item.account_einvoice_serial = einvoice.get('invoice_serial')

        self.sign_invoice_bkav(gui_id_list, data)

    def sign_invoice_bkav(self, gui_id_list, records):
        configs = self.get_bkav_config()
        invoice_guid_list = []
        for gui_id in gui_id_list:
            invoice_guid_list.append({
                "InvoiceGUID": gui_id
            })
        body = {
            "CmdType": 206,
            "CommandObject": invoice_guid_list
        }
        try:
            response = connect_bkav(body, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            _logger.error(response.get('Object'), "nvgiang")
        else:
            for item in records:
                item.einvoice_status = 'sign'
                item.state = 'posted'
