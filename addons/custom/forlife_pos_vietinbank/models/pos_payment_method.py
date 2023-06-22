# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.image import image_data_uri
import base64
import requests

from reportlab.graphics.barcode import createBarcodeDrawing


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('vietinbank', 'Vietinbank')]

    @api.model
    def vnpay_payment_request(self, url, data):
        req = requests.post(url, json=data)
        res = req.json()
        return res
