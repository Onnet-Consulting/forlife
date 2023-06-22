from base64 import b64decode, b64encode
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from odoo import fields, api, models, _, http
import requests
from datetime import datetime, timedelta
import random
import time
import json
from Crypto.PublicKey import RSA
from odoo.exceptions import ValidationError


class ApisVietinBank(models.AbstractModel):
    _name = 'apis.vietinbank'

    def _ramdom_request(self):
        random_hex = ''.join(random.choices('0123456789ABCDEF', k=8))
        milliseconds = int(time.time() * 1000)
        result = f"{random_hex}-{milliseconds}"
        return result

    def _get_header(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'x-ibm-client-secret': params.get_param('vietinbank.client.secret'),
            'x-ibm-client-id': params.get_param('vietinbank.client.id'),
        }

    def _vietin_bank_sign_message(self, message):
        company_sudo = self.env.company.sudo()
        server_private_key = b64decode(company_sudo.vietin_bank_server_private_key)
        private_key = RSA.importKey(server_private_key)
        signer = pkcs1_15.new(private_key)
        hash_obj = SHA256.new(message.encode('utf-8'))
        sig = signer.sign(hash_obj)
        return b64encode(sig).decode('utf-8')

    def _prepare_body(self):
        params = self.env['ir.config_parameter'].sudo()
        date_to = datetime.now().strftime('%d/%m/%Y')
        date_from = (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y')
        request_id = self._ramdom_request()
        provider_id = params.get_param('vietinbank.provider')
        merchant_id = ""
        account_id = "118649946666"
        http_request = http.request.httprequest
        # Get the client's IP address from the request headers
        client_ip = http_request.environ.get('REMOTE_ADDR')
        vals = {
            "requestId": request_id,
            "merchantId": merchant_id,
            "providerId": provider_id,
            "model": "1",
            "account": account_id,
            "fromDate": date_from,
            "toDate": date_to,
            "accountType": "D",
            "collectionType": "d",
            "agencyType": "a",
            "transTime": datetime.now().timestamp(),
            "channel": "ERP",
            "version": "1",
            "clientIP": client_ip,
            "language": "vi",
            "signature": ""
        }
        signature_keys = ['requestId', 'providerId', 'merchantId', 'account']
        unsigned_signature = ''.join([vals[k] for k in signature_keys])
        vals.update({'signature': self._vietin_bank_sign_message(unsigned_signature)})
        return vals

    def get_statement_inquiry(self):
        params = self.env['ir.config_parameter'].sudo()
        req = requests.post(
            url=params.get_param('vietinbank.uri') + '/development/erp/v1/statement/inquiry',
            headers=self._get_header(),
            json=self._prepare_body()
        )
        if req.status_code != 200:
            return False, _("Can't get data from vietinbank")
        data = json.loads(req.text)
        if data['status']['code'] != '1':
            return False, _("Can't get data from vietinbank: Error: %s" % data['status']['message'])
        return True, data

    @api.model
    def get_list_transaction_info(self, args):
        trans_data = self.get_statement_inquiry()
        data = trans_data[1]
        if not trans_data[0]:
            return trans_data
        vals = []
        for item in data.get('transactions', []):
            if 'order' not in item or not item['order']:
                continue
            vals.append({
                'pos_order_id': args[0],
                'payment_method_id': args[1],
                'debit_account': item['corresponsiveAccount'],
                'amount': item['debit'],
                'benefi_account': data['account'],
                'benefi_name': data['companyName'],
                'ref': item['transactionContent'],
                'ref_no': "",
                'effect_date': item['transactionDate'],
                'channel': item['channel'],
            })
        self.env['vietinbank.transaction.model'].create(vals)
        return True, 'success'

    @api.model
    def total_amount(self, ids):
        transaction = self.env['vietinbank.transaction.model'].browse(ids)
        return sum(transaction.mapped('amount'))


class VietinBankModel(models.TransientModel):
    _name = 'vietinbank.transaction.model'
    _description = ''

    pos_order_id = fields.Many2one('pos.order', string='Pos Order')
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment method')
    company_id = fields.Many2one('res.company', string='Company')
    debit_account = fields.Char(string='Debit account')
    amount = fields.Float(string='Amount')
    benefi_account = fields.Char(string='Beneficiary account')
    benefi_name = fields.Char(string='Beneficiary name')
    ref = fields.Char(string='Reference')
    ref_no = fields.Char(string='Ref no')
    effect_date = fields.Date(string='Effective date')
    channel = fields.Char(string='Channel')
