# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from base64 import b64decode
from base64 import b64encode
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_nextpay_config = fields.Boolean(compute='_compute_show_nextpay_config', store=True)
    nextpay_url = fields.Char(string='NextPay Endpoint')
    nextpay_secret_key = fields.Char(string='NextPay Secret Key', help='Each PoS has an unique merchant ID')
    nextpay_merchant_id = fields.Char(string='NextPay Merchant ID')
    nextpay_pos_id = fields.Char(compute='_compute_nextpay_pos_id', store=True, string="ID POS")

    _sql_constraints = [
        ('nextpay_merchant_id_unique', 'unique (nextpay_merchant_id)', 'The NextPay Merchant ID must be unique!')
    ]

    @api.depends('payment_method_ids')
    def _compute_show_nextpay_config(self):
        for config in self:
            config.show_nextpay_config = bool(
                config.payment_method_ids.filtered(
                    lambda payment: not payment.hide_use_payment_terminal
                                    and payment.use_payment_terminal == 'nextpay'))

    @api.depends('nextpay_merchant_id')
    def _compute_nextpay_pos_id(self):
        for config in self:
            config.nextpay_pos_id = str(config.id).zfill(6)

    def _get_nextpay_channel_name(self):
        self.ensure_one()
        return '["{}","{}"]'.format("nextpay_payment_response", self.id)

    def _notify_nextpay_payment_response(self, message):
        self.ensure_one()
        notifications = [
            [self._get_nextpay_channel_name(), 'pos.config/nextpay_payment_response', message]
        ]
        self.env['bus.bus']._sendmany(notifications)
        return True

    @api.model
    def aes_ecb_encrypt(self, key, raw):
        key = key.encode('utf-8')
        raw = json.dumps(raw).encode('utf-8')
        raw = pad(raw, AES.block_size)
        cipher = AES.new(key, AES.MODE_ECB)
        return b64encode(cipher.encrypt(raw)).decode('utf-8')

    @api.model
    def aes_ecb_decrypt(self, key, enc):
        key = key.encode("utf-8")
        enc = b64decode(enc)
        cipher = AES.new(key, AES.MODE_ECB)
        return unpad(cipher.decrypt(enc), AES.block_size).decode('utf-8')
