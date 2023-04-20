# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.image import image_data_uri
import base64
import requests

from reportlab.graphics.barcode import createBarcodeDrawing


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('nextpay', 'NextPay')]

    @api.model
    def nextpay_payment_request(self, url, data):
        req = requests.post(url, json=data)
        return req.json()
