# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from hashlib import sha256


class VNPayController(http.Controller):

    @http.route('/vnpay/ipn', type='raw_json', auth='public', methods=['POST'])
    def received_vnpay_payment_transaction_status(self):
        request_data = request.jsonrequest
        checked_data = self.check_request_data(request_data)
        pos_config = checked_data.get('pos_config')
        if not pos_config:
            return checked_data

        channel_name = 'vnpay_transaction_sync'
        pos_config._send_to_channel(channel_name, request_data)
        return {
            'code': "200",
            "message": "success",
            "traceId": ""
        }

    def check_request_data(self, data):
        client_transaction_code = data.get('clientTransactionCode') or ''
        pos_config_id = client_transaction_code.split('_')[0]
        if not data.get('clientTransactionCode') or not pos_config_id.isdigit():
            return {
                'code': '400',
                'message': 'invalid transaction code',
                'traceId': ""
            }
        pos_config = request.env['pos.config'].sudo().browse(int(pos_config_id))
        merchantMethodCode, orderCode, amount, transactionCode, responseCode = data.get('merchantMethodCode'), \
                                                                               data.get('orderCode'), data.get('amount'), data.get('transactionCode'), \
                                                                               data.get('responseCode')
        secret_code = pos_config.vnpay_ipn_secret_code or ''
        hash_string = secret_code + '|'.join([merchantMethodCode, orderCode, str(amount), transactionCode, responseCode])
        if sha256(hash_string.encode('utf-8')).hexdigest() != data.get('checksum'):
            return {
                "code": "406",
                "message": "invalid checksum",
                'traceId': ""
            }
        return {
            'pos_config': pos_config
        }
