# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from hashlib import sha256
from operator import itemgetter
import json
import logging

_logger = logging.getLogger(__name__)


class VNPayController(http.Controller):

    @http.route('/vnpay/ipn', type='raw_json', auth='public', methods=['POST'])
    def received_vnpay_payment_transaction_status(self):
        request_data = self.check_request_data()
        pos_config = request_data.get('pos_config')
        if not pos_config:
            return request_data

        raw_data = request_data.get('raw_data')
        pos_config._notify_vnpay_payment_response(raw_data)
        return {
            'code': "200",
            "message": "success",
            "traceId": ""
        }

    def check_request_data(self):
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
            client_transaction_code, merchant_method_code, order_code = itemgetter(
                'clientTransactionCode', 'merchantMethodCode', 'orderCode')(data)
            amount, transaction_code, response_code = itemgetter(
                'amount', 'transactionCode', 'responseCode')(data)

            pos_config_id = client_transaction_code.split('_')[0]
            if not client_transaction_code or not pos_config_id.isdigit():
                return {
                    'code': '411',
                    'message': 'invalid transaction code',
                    'traceId': ""
                }
            pos_config = request.env['pos.config'].sudo().browse(int(pos_config_id))

            secret_code = pos_config.vnpay_ipn_secret_code or ''
            hash_string = secret_code + '|'.join(
                [merchant_method_code, order_code, str(amount), transaction_code, response_code])
            if sha256(hash_string.encode('utf-8')).hexdigest() != data.get('checksum'):
                return {
                    "code": "410",
                    "message": "invalid checksum",
                    'traceId': ""
                }
            return {
                'pos_config': pos_config,
                'raw_data': data
            }
        except Exception as e:
            _logger.error(str(e))
            return {
                'code': '411',
                'message': 'invalid transaction code',
                'traceId': ""
            }
