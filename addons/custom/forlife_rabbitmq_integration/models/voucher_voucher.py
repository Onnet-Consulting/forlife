# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import requests


class VoucherVoucher(models.Model):
    _name = 'voucher.voucher'
    _inherit = ['voucher.voucher', 'sync.info.rabbitmq.create', 'odoo.app.logging']
    _create_action = 'update'
    _exchange = 'notification_plan_exchange'
    _routing_key = 'notification_plan_routing_key'

    @api.model
    def domain_record_sync_info(self):
        return [('notification_id', 'not in', (False, '')), ('state', '=', 'sold'), ('type', '=', 'e'), ('partner_id.phone', 'not in', (False, ''))]

    def get_sync_info_value(self):
        return [{
            'program_id': line.program_voucher_id.id,
            'code': line.name,
            'phone_number': line.partner_id.phone,
            'denomination': line.price,
        } for line in self]

    def push_notification_to_app(self):
        app_api_link = {}
        Utility = self.env['res.utility']
        for l in self.env['forlife.app.api.link'].search([]):
            app_api_link.update({l.key: l.value})
        for v in self:
            try:
                link = app_api_link.get(v.brand_id.code)
                if link:
                    param = f'type=pushNotificationbyId&customerId={v.partner_id.phone}&NotiId={v.notification_id}&param={v.name}'
                    result = requests.get(link + param)
                    Utility.create_ir_logging(self._name, result.text, line=str(v.id), func='push_notification_to_app', path=link + param)
                else:
                    message = f"Không tìm thấy api link với mã thương hiệu '{v.brand_id.code}'"
                    Utility.create_ir_logging(self._name, message, line=str(v.id), func='push_notification_to_app')
            except Exception as e:
                Utility.create_ir_logging(self._name, str(e), line=str(v.id), func='push_notification_to_app')

    def action_sync_info_data(self, action):
        res = super().action_sync_info_data(action)
        self.push_notification_to_app()
        return res
