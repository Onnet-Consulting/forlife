# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_show_nextpay_config = fields.Boolean(related='pos_config_id.show_nextpay_config')
    pos_nextpay_url = fields.Char(related='pos_config_id.nextpay_url', readonly=False)
    pos_nextpay_secret_key = fields.Char(related='pos_config_id.nextpay_secret_key', readonly=False)
    pos_nextpay_merchant_id = fields.Char(related='pos_config_id.nextpay_merchant_id', readonly=False)
    pos_nextpay_pos_id = fields.Char(related='pos_config_id.nextpay_pos_id', readonly=False)
