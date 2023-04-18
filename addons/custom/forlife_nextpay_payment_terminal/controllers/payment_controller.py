# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class NextPayController(http.Controller):

    @http.route('/nextpay/ipn', type='json', auth='public', methods=['POST'], raw_json_response=True)
    def received_nextpay_payment_transaction_status(self):
        request_data = request.jsonrequest
        checked_data = self.check_request_data(request_data)
        pos_config = checked_data.get('pos_config')

        if not pos_config:
            return checked_data

        raw_data = checked_data.get('raw_data')
        channel_name = 'nextpay_transaction_sync'
        pos_config._send_to_channel(channel_name, raw_data)
        return {
            "resCode": 200,
            "message": "Success",
        }

    def check_request_data(self, data):
        request_data = data.get('reqData')
        merchant_id = data.get('merchantID')
        if not request_data or not merchant_id:
            return {
                'resCode': '406',
                'message': 'invalid request',
            }
        # search PoS by merchant ID
        pos_config = request.env['pos.config'].sudo().search([('nextpay_merchant_id', '=', merchant_id)], limit=1)
        if not pos_config:
            return {
                'resCode': '406',
                'message': 'merchantID does not exist in Odoo',
            }

        secret_key = pos_config.nextpay_secret_key
        raw_data = request.env['res.utility'].sudo().aes_ecb_decrypt(secret_key, request_data)
        return {
            'raw_data': json.loads(raw_data),
            'pos_config': pos_config
        }
