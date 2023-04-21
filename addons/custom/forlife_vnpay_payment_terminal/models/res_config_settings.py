# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_show_vnpay_config = fields.Boolean(related='pos_config_id.show_vnpay_config')
    pos_vnpay_url = fields.Char(related='pos_config_id.vnpay_url', readonly=False)
    pos_vnpay_secret_code = fields.Char(related='pos_config_id.vnpay_secret_code', readonly=False)
    pos_vnpay_ipn_secret_code = fields.Char(related='pos_config_id.vnpay_ipn_secret_code', readonly=False)
    pos_vnpay_merchant_code = fields.Char(related='pos_config_id.vnpay_merchant_code', readonly=False)
    pos_vnpay_terminal_code = fields.Char(related='pos_config_id.vnpay_terminal_code', readonly=False)
    pos_vnpay_merchant_method_code_card = fields.Char(related='pos_config_id.vnpay_merchant_method_code_card',
                                                      readonly=False)
    pos_vnpay_success_url = fields.Char(related='pos_config_id.vnpay_success_url', readonly=False)
    pos_vnpay_cancel_url = fields.Char(related='pos_config_id.vnpay_cancel_url', readonly=False)
