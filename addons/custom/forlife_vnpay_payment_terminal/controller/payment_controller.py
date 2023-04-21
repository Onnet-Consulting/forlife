# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from hashlib import sha256
from operator import itemgetter
import logging

_logger = logging.getLogger(__name__)


class VNPayController(http.Controller):

    @http.route('/vnpay/ipn', type='raw_json', auth='public', methods=['POST'])
    def received_vnpay_payment_transaction_status(self):
        request_data = request.jsonrequest
        checked_data = self.check_request_data(request_data)
        pos_config = checked_data.get('pos_config')
        if not pos_config:
            return checked_data

        pos_config._notify_vnpay_payment_response(request_data)
        return {
            'code': "200",
            "message": "success",
            "traceId": ""
        }

    def check_request_data(self, data):
        try:
            client_transaction_code, merchant_method_code, order_code = itemgetter(
                'clientTransactionCode', 'merchantMethodCode', 'orderCode')(data)
            amount, transaction_code, response_code = itemgetter(
                'amount', 'transactionCode', 'responseCode')(data)

            client_transaction_code = ''
            pos_config_id = client_transaction_code.split('_')[0]
            if client_transaction_code or not pos_config_id.isdigit():
                return {
                    'code': '400',
                    'message': 'invalid transaction code',
                    'traceId': ""
                }
            pos_config = request.env['pos.config'].sudo().browse(int(pos_config_id))

            secret_code = pos_config.vnpay_ipn_secret_code or ''
            hash_string = secret_code + '|'.join(
                [merchant_method_code, order_code, str(amount), transaction_code, response_code])
            if sha256(hash_string.encode('utf-8')).hexdigest() != data.get('checksum'):
                return {
                    "code": "406",
                    "message": "invalid checksum",
                    'traceId': ""
                }
            return {
                'pos_config': pos_config
            }
        except Exception as e:
            _logger.error(str(e))
            return {
                'code': '400',
                'message': 'invalid transaction code',
                'traceId': ""
            }
