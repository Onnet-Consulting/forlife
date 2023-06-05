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

    def get_sync_create_data(self):
        app_api_link = self.env['forlife.app.api.link'].search([])
        data = []
        for v in self:
            data.append({
                'program_id': v.program_voucher_id.id,
                'code': v.name,
                'phone_number': v.partner_id.phone,
                'denomination': v.price,
            })
            try:
                res = app_api_link.filtered(lambda f: f.key == (v.brand_id.code or ''))
                if res:
                    param = f'type=pushNotificationVIP&id={v.notification_id}&voucher={v.name}&gift=&customerId={v.partner_id.phone}'
                    requests.get(res[0].value + param)
            except:
                pass
        return data
