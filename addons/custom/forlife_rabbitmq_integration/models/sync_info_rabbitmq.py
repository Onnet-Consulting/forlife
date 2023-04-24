# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class SyncInfoRabbitmq(models.AbstractModel):
    _name = 'sync.info.rabbitmq'
    _description = 'Sync Info RabbitMQ'

    def action_new_record(self):
        ...

    def action_update_record(self):
        ...

    def action_delete_record(self):
        ...

    def check_update_info(self, values):
        ...

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res.sudo().with_delay().action_new_record()
        return res

    def write(self, values):
        res = super().write(values)
        data = self.check_update_info(values)
        if data:
            self.sudo().action_update_record(data)
        return res

    def unlink(self):
        record_ids = self.ids
        res = super().unlink()
        if record_ids:
            self.sudo().action_delete_record(record_ids)
        return res
