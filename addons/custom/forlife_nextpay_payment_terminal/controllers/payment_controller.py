# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class NextPayController(http.Controller):

    @http.route('/nextpay/ipn', type='raw_json', auth='public', methods=['POST'])
    def received_nextpay_payment_transaction_status(self):
        checked_data = self.check_request_data()
        pos_config = checked_data.get('pos_config')

        if not pos_config:
            return checked_data

        raw_data = checked_data.get('raw_data')
        pos_config.sudo()._notify_nextpay_payment_response(raw_data)
        return {
            "resCode": 200,
            "message": "Success",
        }

    def check_request_data(self):
        invalid_response = {
            'resCode': '406',
            'message': 'invalid request',
        }
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
            request_data = data.get('reqData')
            merchant_id = data.get('merchantID')
            if not request_data or not merchant_id:
                return invalid_response
        except Exception:
            return invalid_response

        # search PoS by merchant ID
        pos_config = request.env['pos.config'].sudo().search([('nextpay_merchant_id', '=', merchant_id)], limit=1)
        if not pos_config:
            return {
                'resCode': '406',
                'message': 'merchantID does not exist in Odoo',
            }

        secret_key = pos_config.nextpay_secret_key
        raw_data = request.env['pos.config'].sudo().aes_ecb_decrypt(secret_key, request_data)
        return {
            'raw_data': json.loads(raw_data),
            'pos_config': pos_config
        }
