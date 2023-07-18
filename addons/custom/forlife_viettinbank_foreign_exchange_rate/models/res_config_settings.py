# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vietin_bank_server_private_key = fields.Binary(related='company_id.vietin_bank_server_private_key', readonly=False)
    vietin_bank_exchange_rate_url = fields.Char(related='company_id.vietin_bank_exchange_rate_url', readonly=False)
    vietin_bank_client_id = fields.Char(related='company_id.vietin_bank_client_id', readonly=False)
    vietin_bank_client_secret = fields.Char(related='company_id.vietin_bank_client_secret', readonly=False)
    vietin_bank_provider_id = fields.Char(related='company_id.vietin_bank_provider_id', readonly=False)
    show_vietin_bank_setting = fields.Boolean(related='company_id.show_vietin_bank_setting')

    # sửa lại hàm base enterprice để hiển thị lỗi trả về rõ dàng hơn.
    def update_currency_rates_manually(self):
        self.ensure_one()
        update_currency = self.company_id.update_currency_rates()
        if not (update_currency[0]):
            raise UserError(
                _('Unable to connect to the online exchange rate platform. The web service may be temporary down. Please try again in a moment. Error: %s' % (
                update_currency[1])))
