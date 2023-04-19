# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, time

import gzip
import base64
import json
import requests
from Crypto.Cipher import AES

URL_WEB_SERVICE_BKAV = "https://wsdemo.ehoadon.vn/WSPublicEhoadon.asmx"


def connect_bkav(data):
    # Compress the data using gzip
    compressed_data = gzip.compress(str(data).encode("utf-8"))

    # Decode the partner token
    partner_token = "+RbIW9pjjZZF7sxDNZ6rynW8xYRUsVuIUhdBfP2IiqA=:TmpaSIE1gUegLz3fjvvTAg=="
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
                          <partnerGUID>2f986fea-9b54-48a6-b0a9-11db6f3ab474</partnerGUID>
                          <CommandData>{encrypted_data}</CommandData>
                      </ExecCommand>
                   </soapenv:Body>
                </soapenv:Envelope>
            """
    proxies = get_proxies()

    response = requests.post(URL_WEB_SERVICE_BKAV, headers=headers, data=soap_request, timeout=3.5)

    mes = response.content.decode("utf-8")

    start_index = mes.index("<ExecCommandResult>") + len("<ExecCommandResult>")
    end_index = mes.index("</ExecCommandResult>")
    res = response.content[start_index:end_index]

    decoded_string = base64.b64decode(res)
    cipher2 = AES.new(encryption_key, AES.MODE_CBC, iv)
    plaintext = cipher2.decrypt(decoded_string)
    plaintext = plaintext.rstrip(plaintext[-4:])
    decode = gzip.decompress(plaintext).decode()
    response_bkav = json.loads(decode)

    if response_bkav['Status'] == 0:
        status_index = response_bkav['Object'].index('"Status":') + len('"Status":')
        mes_index_s = response_bkav['Object'].index('"MessLog":"') + len('"MessLog":"')
        mes_index_e = response_bkav['Object'].index('"}]')
        response_status = response_bkav['Object'][status_index]
        response_mes = response_bkav['Object'][mes_index_s:mes_index_e]
    else:
        response_status = '1'
        response_mes = response_bkav['Object']

    return {
        'status': response_status,
        'message': response_mes
    }


class AccountMove(models.Model):
    _inherit = 'account.move'

    exists_bkav = fields.Boolean(default=False)
    is_post_bkav = fields.Boolean(default=False, string="Tạo hóa đơn cuối ngày BKAV?")
    company_type = fields.Selection(related="partner_id.company_type")

    def create_invoice_bkav(self):
        data = {
            "CmdType": 100,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceTypeID": 1,
                        "InvoiceDate": self.invoice_date.isoformat() if self.invoice_date else '',
                        "BuyerName": self.partner_id.name,
                        "BuyerTaxCode": self.partner_id.vat or '',
                        "BuyerUnitName": self.partner_id.name or '',
                        "BuyerAddress": self.partner_id.country_id.name or '',
                        "BuyerBankAccount": self.partner_bank_id.id or '',
                        "PayMethodID": 1,
                        "ReceiveTypeID": 3,
                        "ReceiverEmail": self.company_id.email or '',
                        "ReceiverMobile": self.company_id.mobile or '',
                        "ReceiverAddress": self.company_id.street or '',
                        "ReceiverName": self.company_id.name or '',
                        "Note": "",
                        "BillCode": "",
                        "CurrencyID": self.company_id.currency_id.name or '',
                        "ExchangeRate": 1.0,
                        "InvoiceForm": "",
                        "InvoiceSerial": "",
                        "InvoiceNo": 0,
                        "OriginalInvoiceIdentify": "[C23TAA/001]_[TM]_[0000001]",
                    },
                    "ListInvoiceDetailsWS": [
                        {
                            "ItemName": line.name or '',
                            "UnitName": "Gói",
                            "Qty": line.quantity or '',
                            "Price": line.price_unit or '',
                            "Amount": line.price_subtotal or '',
                            "TaxRateID": 3,
                            "TaxRate": 10,
                            "TaxAmount": 60000.0,
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
        response = connect_bkav(data)
        if response.get('status') == '1':
            self.message_post(body=(response.get('message')))
        else:
            self.message_post(body=_('Đã tạo thành công hóa đơn trên BKAV!!'))
            self.exists_bkav = True

    def update_invoice_bkav(self):
        data = {
            "CmdType": 200,
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceTypeID": 1,
                        "InvoiceDate": self.invoice_date.isoformat() if self.invoice_date else '',
                        "BuyerName": self.partner_id.name,
                        "BuyerTaxCode": self.partner_id.vat or '',
                        "BuyerUnitName": self.partner_id.name or '',
                        "BuyerAddress": self.partner_id.country_id.name or '',
                        "BuyerBankAccount": self.partner_bank_id.id or '',
                        "PayMethodID": 1,
                        "ReceiveTypeID": 3,
                        "ReceiverEmail": self.company_id.email or '',
                        "ReceiverMobile": self.company_id.mobile or '',
                        "ReceiverAddress": self.company_id.street or '',
                        "ReceiverName": self.company_id.name or '',
                        "Note": "",
                        "BillCode": "",
                        "CurrencyID": self.company_id.currency_id.name or '',
                        "ExchangeRate": 1.0,
                        "InvoiceForm": "",
                        "InvoiceSerial": "",
                        "InvoiceNo": 0,
                        "OriginalInvoiceIdentify": "[C23TAA/001]_[TM]_[0000001]",
                    },
                    "ListInvoiceDetailsWS": [
                        {
                            "ItemName": line.name or '',
                            "UnitName": "",
                            "Qty": line.quantity or '',
                            "Price": line.price_unit or '',
                            "Amount": line.price_subtotal or '',
                            "TaxRateID": 3,
                            "TaxRate": 10,
                            "TaxAmount": 60000.0,
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
        response = connect_bkav(data)
        if response.get('status') == '1':
            self.message_post(body=(response.get('message')))
        else:
            self.message_post(body=_('Đã cập nhật thành công hóa đơn trên BKAV!!'))


    def cancel_invoice_bkav(self):
        data_delete = {
            "CmdType": 202,
            "CommandObject": [{
                "PartnerInvoiceID": self.id,
            }]
        }
        response = connect_bkav(data_delete)
        if response.get('status') == '1':
            self.message_post(body=(response.get('message')))
        else:
            self.message_post(body=_('Đã Hủy thành công hóa đơn trên BKAV!!'))

    def delete_invoice_bkav(self):
        data_delete = {
            "CmdType": 301,
            "CommandObject": [{
                "PartnerInvoiceID": self.id,
            }]
        }
        response = connect_bkav(data_delete)
        if response.get('status') == '1':
            self.message_post(body=(response.get('message')))
        else:
            self.message_post(body=_('Đã xóa thành công hóa đơn trên BKAV!!'))

    def unlink(self):
        res = super().action_post()
        if self.exists_bkav:
            self.delete_invoice_bkav()
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.create_invoice_bkav()
        return res

    def action_post(self):
        res = super().action_post()
        if self.exists_bkav:
            self.update_invoice_bkav()
        else:
            self.create_invoice_bkav()
        return res

    def post_invoice_to_bkav_end_day(self):
        today = datetime.now().date()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)
        invoices = self.search([('is_post_bkav', '=', False),
                                ('create_date', '>=', start_of_day), ('create_date', '<=', end_of_day)])
        invoice_lines = []
        if len(invoices):
            for inv in invoices:
                invoice_lines.extend(inv.invoice_line_ids.ids)
            inv_bkav = self.create({
                'partner_id': self.env.ref('base.partner_admin').id,
                'invoice_date': today,
                'is_post_bkav': True,
                'invoice_description': f"Hóa đơn bán lẻ cuối ngày {today.strftime('%Y/%m/%d')}",
                'invoice_line_ids': [(6, 0, invoice_lines)],
            })
            if inv_bkav.exists_bkav:
                for inv in invoices:
                    inv.is_post_bkav = True