# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, exceptions
import requests
import logging
import webbrowser

_logger = logging.getLogger(__name__)
NHANH_BASE_AUTH_URL = 'https://nhanh.vn/oauth'
NHANH_BASE_URL = 'https://open.nhanh.vn/api'


class NhanhBrandConfig(models.Model):
    _name = 'nhanh.brand.config'
    _description = 'Nhanh config for per brand'

    brand_id = fields.Many2one('res.brand', string="Brand", required=1)
    active = fields.Boolean('Active', default=True)
    nhanh_business_id = fields.Char(string="Business Id")
    nhanh_app_id = fields.Char(string="App Id")
    nhanh_secret_key = fields.Char(string="Secret Key")
    nhanh_access_code = fields.Char(string="Access Code")
    nhanh_access_token = fields.Char(string="Access Token")
    nhanh_access_token_expired = fields.Datetime(string="Access Token Expired")
    nhanh_return_link = fields.Char(string="Return Link")
    link_get_access_code = fields.Char(string='Link Get access code', compute='compute_link_get_access_code')

    @api.constrains('brand_id', 'active')
    def _contrains_brand_active(self):
        for item in self:
            exist_brand_config = self.env['nhanh.brand.config'].sudo().search_count(
                [('brand_id', '=', item.brand_id.id), ('id', '!=', item.id)])
            if exist_brand_config:
                raise exceptions.ValidationError('Đã tồn tại cấu hình cho chi nhánh này!')

    @api.depends('nhanh_app_id', 'nhanh_return_link')
    def compute_link_get_access_code(self):
        for item in self:
            if item.nhanh_app_id and item.nhanh_return_link:
                item.link_get_access_code = f'{NHANH_BASE_AUTH_URL}?version={2.0}&appId={item.nhanh_app_id}&returnLink={item.nhanh_return_link}'
            else:
                item.link_get_access_code = False

    def action_get_nhanh_access_code(self):
        get_access_code_url = f'{NHANH_BASE_AUTH_URL}?version={2.0}&appId={self.nhanh_app_id}&returnLink={self.nhanh_return_link}'
        webbrowser.open(get_access_code_url)

    def check_connect_to_nhanh(self):
        url = f"{NHANH_BASE_URL}/order/index?version=2.0&appId={self.nhanh_app_id}&businessId={self.nhanh_business_id}&accessToken={self.nhanh_access_token}"
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

        # show success message
        url = f"{NHANH_BASE_AUTH_URL}/access_token?version=2.0&appId={self.nhanh_app_id}" \
              f"&businessId={self.nhanh_business_id}&accessCode={self.nhanh_access_code}" \
              f"&secretKey={self.nhanh_secret_key}"
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
                self.update({
                    'nhanh_access_token': res['accessToken'],
                    'nhanh_business_id': res['businessId'],
                    'nhanh_access_token_expired': res['expiredDateTime'],
                })

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
            }
        }

    def remove_nhanh_config(self):
        self.nhanh_business_id = None
        self.nhanh_app_id = None
        self.nhanh_secret_key = None
        self.nhanh_access_code = None
        self.nhanh_access_token = None
        self.nhanh_access_token_expired = None