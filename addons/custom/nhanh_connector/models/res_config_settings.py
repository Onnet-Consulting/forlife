# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.nhanh_connector.models.constant import get_proxies
import requests
import logging
import webbrowser
from datetime import datetime

_logger = logging.getLogger(__name__)
NHANH_BASE_AUTH_URL = 'https://nhanh.vn/oauth'
NHANH_BASE_URL = 'https://open.nhanh.vn/api'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhanh_business_id = fields.Char(string="Business Id", config_parameter='nhanh_connector.nhanh_business_id')
    nhanh_app_id = fields.Char(string="App Id", config_parameter='nhanh_connector.nhanh_app_id')
    nhanh_secret_key = fields.Char(string="Secret Key", config_parameter='nhanh_connector.nhanh_secret_key')
    nhanh_access_code = fields.Char(string="Access Code", config_parameter='nhanh_connector.nhanh_access_code')
    nhanh_access_token = fields.Char(string="Access Token", config_parameter='nhanh_connector.nhanh_access_token')
    nhanh_access_token_expired = fields.Datetime(string="Access Token Expired", config_parameter='nhanh_connector.nhanh_access_token_expired')
    nhanh_return_link = fields.Char(string="Return Link", config_parameter='nhanh_connector.nhanh_return_link')
    link_get_access_code = fields.Char(string='Link Get access code', compute='compute_link_get_access_code')

    @api.depends('nhanh_app_id', 'nhanh_return_link')
    def compute_link_get_access_code(self):
        for item in self:
            if item.nhanh_app_id and item.nhanh_return_link:
                item.link_get_access_code = f'{NHANH_BASE_AUTH_URL}?version={2.0}&appId={item.nhanh_app_id}&returnLink={item.nhanh_return_link}'
            else:
                item.link_get_access_code = False

    def action_get_nhanh_access_code(self):
        get_param = self.env['ir.config_parameter'].sudo()
        get_pr_nhanh_app_id = get_param.get_param('nhanh_connector.nhanh_app_id', False)
        get_pr_nhanh_return_link = get_param.get_param('nhanh_connector.nhanh_return_link', False)
        get_access_code_url = f'{NHANH_BASE_AUTH_URL}?version={2.0}&appId={get_pr_nhanh_app_id}&returnLink={get_pr_nhanh_return_link}'
        webbrowser.open(get_access_code_url)

    def check_connect_to_nhanh(self):
        get_param = self.env['ir.config_parameter'].sudo()
        get_pr_nhanh_app_id = get_param.get_param('nhanh_connector.nhanh_app_id', False)
        get_pr_nhanh_business_id = get_param.get_param('nhanh_connector.nhanh_business_id', False)
        get_pr_nhanh_access_token = get_param.get_param('nhanh_connector.nhanh_access_token', False)
        url = f"{NHANH_BASE_URL}/order/index?version=2.0&appId={get_pr_nhanh_app_id}" \
              f"&businessId={get_pr_nhanh_business_id}&accessToken={get_pr_nhanh_access_token}"
        # Setup proxies
        # Get all orders from previous day to today from Nhanh.vn
        try:
            res_server = requests.post(url)
        except Exception as ex:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Failed"),
                    'message': _('Connect failed!'),
                    'sticky': False,
                }
            }
        get_order_status = 1
        try:
            res = res_server.json()
        except Exception as ex:
            get_order_status = 0
            _logger.info(f'Check connect failed from NhanhVn {ex}')
        if get_order_status:
            if res['code'] == 0:
                if res['messages'][0] != 'No records':
                    get_order_status = 0
                    _logger.info(f'Check connect failed with code 0 error {res["messages"]}')
                else:
                    _logger.info(f'No records')
            else:
                _logger.info(f'Check token success')
        title = _("Successfully!") if get_order_status else _("Failed")
        message = _('Connect to NhanhVn successfully!') if get_order_status else _(
            'Get access_token from NhanhVn failed!')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }
        }

    def action_get_nhanh_access_token(self):
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo()
        get_pr_nhanh_app_id = get_param.get_param('nhanh_connector.nhanh_app_id', False)
        get_pr_nhanh_access_code = get_param.get_param('nhanh_connector.nhanh_access_code', False)
        get_pr_nhanh_business_id = get_param.get_param('nhanh_connector.nhanh_business_id', False)
        get_pr_nhanh_secret_key = get_param.get_param('nhanh_connector.nhanh_secret_key', False)

        # show success message
        url = f"{NHANH_BASE_AUTH_URL}/access_token?version=2.0&appId={get_pr_nhanh_app_id}" \
              f"&businessId={get_pr_nhanh_business_id}&accessCode={get_pr_nhanh_access_code}" \
              f"&secretKey={get_pr_nhanh_secret_key}"
        # Setup proxies
        # Get all orders from previous day to today from Nhanh.vn
        try:
            res_server = requests.post(url)
        except Exception as ex:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Failed"),
                    'message': _('Connect failed!'),
                    'sticky': False,
                }
            }
        get_token_status = 1
        try:
            res = res_server.json()
        except Exception as ex:
            get_token_status = 0
            _logger.info(f'Get access_token from NhanhVn error {ex}')
        if get_token_status:
            if res['code'] == 0:
                get_token_status = 0
                _logger.info(f'Get access_token error {res["message"]}')
            else:
                self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_access_token', res['accessToken'])
                self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_business_id', res['businessId'])
                self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_access_token_expired', res['expiredDateTime'])
                self.env['ir.config_parameter'].get_param('nhanh_connector.nhanh_access_token', False)
                self.env['ir.config_parameter'].get_param('nhanh_connector.nhanh_business_id', False)
                self.env['ir.config_parameter'].get_param('nhanh_connector.nhanh_access_token_expired', False)

        title = _("Successfully!") if get_token_status else _("Failed")
        message = _('Get access_token from NhanhVn successfully!') if get_token_status else _(
            'Get access_token from NhanhVn failed!')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def remove_nhanh_config(self):
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_business_id', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_app_id', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_secret_key', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_access_code', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_access_token', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_return_link', '')
        self.env['ir.config_parameter'].set_param('nhanh_connector.nhanh_access_token_expired', '')
