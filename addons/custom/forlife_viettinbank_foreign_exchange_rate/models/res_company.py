# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

from base64 import (b64encode, b64decode)
import json
import requests
import time
import logging

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.Signature import pkcs1_15

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA1
from odoo.exceptions import ValidationError, UserError

VN_COMPANY_CODES = [
    '1200'
]
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(selection_add=[('vietin', 'Vietin Bank')], default='vietin')
    vietin_bank_server_private_key = fields.Binary(string='Server Private Key')
    vietin_bank_exchange_rate_url = fields.Char(string='Exchange Rate URL')
    vietin_bank_client_id = fields.Char(string='Client ID')
    vietin_bank_client_secret = fields.Char(string='Client Secret')
    vietin_bank_provider_id = fields.Char(string='Provider ID')
    show_vietin_bank_setting = fields.Boolean(compute='_compute_show_vietin_bank_setting')

    @api.depends('currency_provider')
    def _compute_show_vietin_bank_setting(self):
        for rec in self:
            rec.show_vietin_bank_setting = rec.currency_provider == 'vietin'

    @api.depends('country_id')
    def _compute_currency_provider(self):
        super()._compute_currency_provider()
        for record in self:
            record.currency_provider = 'vietin'

    def _parse_vietin_data(self, available_currencies):
        data = self._vietin_bank_send_request_exchange_rate()
        if data['status']['code'] != '0':
            raise ValidationError(data)
        response_exchange_rates = data.get('ForeignExchangeRateInfo', [])
        available_currency_names = available_currencies.mapped('name')
        date_rate = fields.Date.context_today(self)
        rates_dict = {}
        for res_rate in response_exchange_rates:
            currency_name = res_rate['Currency']
            if currency_name not in available_currency_names:
                continue
            foreign_rate = float(res_rate['Sell_Rate'])
            foreign_rate = 1 / foreign_rate if foreign_rate != 0 else 0
            rates_dict[currency_name] = (foreign_rate, date_rate)
        if 'VND' in available_currency_names:
            rates_dict['VND'] = (1.0, date_rate)
        return rates_dict

    def _vietin_bank_send_request_exchange_rate(self):
        company_sudo = self.env.company.sudo()
        url = company_sudo.vietin_bank_exchange_rate_url
        client_id = company_sudo.vietin_bank_client_id
        client_secret = company_sudo.vietin_bank_client_secret
        request_data = self._vietin_bank_prepare_exchange_rate_request_data()
        headers = {
            'Content-Type': 'application/json',
            'x-ibm-client-secret': client_secret,
            'x-ibm-client-id': client_id
        }
        response = requests.post(url, json=request_data, headers=headers)
        if response.status_code != 200:
            raise ValidationError(response.text)
        data = response.json()
        return data

    def _vietin_bank_prepare_exchange_rate_request_data(self):
        company_sudo = self.env.company.sudo()
        provider_id = company_sudo.vietin_bank_provider_id
        request_data = {
            'requestId': str(time.time()),
            'providerId': provider_id,
            'merchantId': "",
            "trans_date": fields.Date.context_today(self).strftime('%m/%d/%Y'),
            "language": 'vi',
            'channel': 'WEB',
            'version': "1.0.1",
            "clientIP": ''
        }

        signature_keys = ['requestId', 'trans_date']

        unsigned_signature = ''.join([request_data[k] for k in signature_keys])
        signed_signature = self._vietin_bank_sign_message(unsigned_signature)
        request_data.update({'signature': signed_signature})
        return request_data

    def _vietin_bank_send_request_inquiry(self):
        company_sudo = self.env.company.sudo()
        url = "https://api-uat.vietinbank.vn/vtb-api-uat/development/erp/v1/statement/inquiry"
        client_id = company_sudo.vietin_bank_client_id
        client_secret = company_sudo.vietin_bank_client_secret
        request_data = self._vietin_bank_prepare_inquiry_request_data()
        headers = {
            'Content-Type': 'application/json',
            'x-ibm-client-secret': client_secret,
            'x-ibm-client-id': client_id
        }
        response = requests.post(url, json=request_data, headers=headers)
        data = response.json()
        return data

    def _vietin_bank_prepare_inquiry_request_data(self):
        request_data = {
            "requestId": "343q433410001",
            "merchantId": "",
            "providerId": "HONDA",
            "model": "1",
            "account": "118649946666 ",
            "fromDate": "12/06/2023",
            "accountType": "D",
            "collectionType": "d",
            "agencyType": "a",
            "transTime": "20230618050101",
            "channel": "ERP",
            "version": "1",
            "clientIP": "",
            "language": "vi",
            "signature": ""
        }

        signature_keys = ['requestId', 'providerId', 'merchantId', 'account']

        unsigned_signature = ''.join([request_data[k] for k in signature_keys])
        signed_signature = self._vietin_bank_sign_message(unsigned_signature)
        request_data.update({"signature": signed_signature})
        return request_data

    def _vietin_bank_prepare_register_request_data(self):

        data = {
            "requestId": "VNPT1577878788",
            "providerId": "HONDA",
            "merchantId": "",
            "model": "1",
            "account": "118649946666",
            "accountType": "D",
            "agencyType": "",
            "collectionType": "",
            "notifyType": "A",
            "outputFolder": "ERP/CASPER/OUT",
            "cronExpress": "00/1****",
            "transTime": "20230618050101",
            "channel": "ERP",
            "version": "1",
            "clientIP": "",
            "language": "vi",
            "signature": ""
        }
        signature_keys = ['requestId', 'providerId', 'merchantId', 'agencyType', "account",
                          "notifyType", "cronExpress", "transTime", "channel", "version", "clientIP", "language"]

        unsigned_signature = ''.join([data[k] for k in signature_keys])
        signed_signature = self._vietin_bank_sign_message(unsigned_signature)
        data.update({"signature": signed_signature})

        return data

    def _vietin_bank_send_register_request(self):
        company_sudo = self.env.company.sudo()
        url = company_sudo.vietin_bank_exchange_rate_url
        url = "https://api-uat.vietinbank.vn/vtb-api-uat/development/erp/v1/statement/register"
        client_id = company_sudo.vietin_bank_client_id
        client_secret = company_sudo.vietin_bank_client_secret
        request_data = self._vietin_bank_prepare_register_request_data()
        headers = {
            'Content-Type': 'application/json',
            'x-ibm-client-secret': client_secret,
            'x-ibm-client-id': client_id
        }
        response = requests.post(url, json=request_data, headers=headers)
        data = response.json()
        return data

    def _vietin_bank_sign_message(self, message):
        company_sudo = self.env.company.sudo()
        server_private_key = b64decode(company_sudo.vietin_bank_server_private_key)
        private_key = RSA.importKey(server_private_key)
        signer = pkcs1_15.new(private_key)
        hash_obj = SHA256.new(message.encode('utf-8'))
        sig = signer.sign(hash_obj)
        return b64encode(sig).decode('utf-8')

    # sửa lại hàm base enterprice để hiển thị lỗi trả về rõ dàng hơn.
    def update_currency_rates(self):
        ''' This method is used to update all currencies given by the provider.
        It calls the parse_function of the selected exchange rates provider automatically.

        For this, all those functions must be called _parse_xxx_data, where xxx
        is the technical name of the provider in the selection field. Each of them
        must also be such as:
            - It takes as its only parameter the recordset of the currencies
              we want to get the rates of
            - It returns a dictionary containing currency codes as keys, and
              the corresponding exchange rates as its values. These rates must all
              be based on the same currency, whatever it is. This dictionary must
              also include a rate for the base currencies of the companies we are
              updating rates from, otherwise this will result in an error
              asking the user to choose another provider.

        :return: True if the rates of all the records in self were updated
                 successfully, False if at least one wasn't.
        '''
        active_currencies = self.env['res.currency'].search([])
        rslt = True
        error = ''
        for (currency_provider, companies) in self._group_by_provider().items():
            parse_function = getattr(companies, '_parse_' + currency_provider + '_data')
            try:
                parse_results = parse_function(active_currencies)
                companies._generate_currency_rates(parse_results)
            except Exception as e:
                rslt = False
                error = e
                _logger.exception(
                    'Unable to connect to the online exchange rate platform %s. The web service may be temporary down' % (currency_provider))
        return rslt, error