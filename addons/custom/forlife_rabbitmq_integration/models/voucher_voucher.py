# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import requests


class VoucherVoucher(models.Model):
    _name = 'voucher.voucher'
    _inherit = ['voucher.voucher', 'sync.info.rabbitmq.create']
    _create_action = 'update'
    _exchange = 'notification_plan_exchange'
    _routing_key = 'notification_plan_routing_key'

    def domain_record_sync_info(self):
        return self.filtered(lambda f: f.notification_id and f.state == 'sold' and
                                       f.type == 'e' and (f.order_pos or f.sale_id) and f.partner_id and f.partner_id.phone)

    def get_sync_info_value(self):
        return [{
            'program_id': line.program_voucher_id.id,
            'code': line.name,
            'phone_number': line.partner_id.phone,
            'denomination': line.price,
        } for line in self]

    def push_notification_to_app(self):
        app_api_link = {}
        for l in self.env['forlife.app.api.link'].search([]):
            app_api_link.update({l.key: l.value})
        for v in self:
            try:
                link = app_api_link.get(v.brand_id.code)
                if link:
                    param = f'type=pushNotificationVIP&id={v.notification_id}&voucher={v.name}&gift=&customerId={v.partner_id.phone}'
                    requests.get(link + param)
            except:
                pass

    def action_sync_info_data(self, action):
        res = super().action_sync_info_data(action)
        self.push_notification_to_app()
        return res
