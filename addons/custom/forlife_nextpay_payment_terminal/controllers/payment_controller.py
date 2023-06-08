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

        # in case multiple POS have the same merchant ID, so the steps to get correct pos.config is:
        # 0. search pos.config(s) by merchant ID
        # 1. pick secret key from random pos.config
        # 2. decode raw data
        # 3. extract pos.config ID from orderID (the unique ID of payment line in POS)
        # 4. filter pos.config to get exactly the POS we want
        pos_configs = request.env['pos.config'].sudo().search([('nextpay_merchant_id', '=', merchant_id)])
        if not pos_configs:
            return {
                'resCode': '406',
                'message': 'merchantID does not exist in Odoo',
            }

        secret_key = pos_configs[0].nextpay_secret_key
        try:
            raw_data = request.env['pos.config'].sudo().aes_ecb_decrypt(secret_key, request_data)
            raw_data = json.loads(raw_data)
            order_id = raw_data.get('orderId')
            pos_config_id = int(order_id.split('_')[0])
            pos_config = pos_configs.filtered(lambda x: x.id == pos_config_id)
            if pos_config:
                return {
                    'raw_data': raw_data,
                    'pos_config': pos_config
                }
        except Exception:
            pass
        return invalid_response
