# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

from base64 import (b64encode, b64decode)
import json
import requests
import time

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

VN_COMPANY_CODES = [
    '1200'
]


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

    # FIXME: add real API here
    def _parse_vietin_data(self, available_currencies):
        data = self._vietin_bank_send_request_exchange_rate()
        if data['status']['code'] != '0':
            return
        rates_dict = {}
        rates_dict['VND'] = (1.0, fields.Date.context_today(self))
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
        response = requests.post(url, json=json.dumps(request_data), headers=headers)
        data = response.json()
        return data

    def _vietin_bank_prepare_exchange_rate_request_data(self):
        company_sudo = self.env.company.sudo()
        provider_id = company_sudo.vietin_bank_provider_id
        request_data = {
            'requestId': str(time.time()),
            'providerId': provider_id,
            'merchantId': "",
            "trans_date": fields.Date.context_today(self).strftime('%d/%m/%Y'),
            "language": 'vi',
            'channel': 'WEB',
            'version': "1.0.1",
            "clientIP": ''
        }
        signature_keys = ['requestId', 'providerId', 'merchantId',
                          'trans_date', 'clientIP', 'channel', 'version', 'language']

        unsigned_signature = ''.join([request_data[k] for k in signature_keys])
        signed_signature = self._vietin_bank_sign_message(unsigned_signature)
        request_data.update({'signature': signed_signature})
        return request_data

    def _vietin_bank_sign_message(self, message):
        company_sudo = self.env.company.sudo()
        digest = SHA256.new()
        digest.update(message.encode('utf-8'))
        server_private_key = b64decode(company_sudo.vietin_bank_server_private_key)
        private_key = RSA.importKey(server_private_key)
        # Sign the message
        signer = PKCS1_v1_5.new(private_key)
        sig = signer.sign(digest)
        return b64encode(sig).decode('utf-8')
