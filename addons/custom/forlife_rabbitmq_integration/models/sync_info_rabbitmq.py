# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pika
import json


class SyncInfoRabbitmqCore(models.AbstractModel):
    _name = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Core'

    def get_rabbitmq_queue_by_model_name(self, model_name):
        rabbitmq_queue = self.env['rabbitmq.queue'].search([('model_name', '=', model_name)])
        if not rabbitmq_queue:
            raise ValueError(_("RabbitQM queue by model name '%s' not found !") % model_name)
        return rabbitmq_queue[0]

    def push_message_to_rabbitmq(self, data, action):
        rabbitmq_queue = self.get_rabbitmq_queue_by_model_name(self._name)
        rabbitmq_connection = rabbitmq_queue.rabbitmq_connection_id
        credentials = pika.PlainCredentials(username=rabbitmq_connection.username, password=rabbitmq_connection.password)
        parameter = pika.ConnectionParameters(host=rabbitmq_connection.host, port=rabbitmq_connection.port, credentials=credentials)
        connection = pika.BlockingConnection(parameter)
        channel = connection.channel()
        channel.queue_declare(queue=rabbitmq_queue.queue_name)
        message = {
            'action': action,
            'target': rabbitmq_queue.target,
            'data': data
        }
        message = json.dumps(message).encode('utf-8')
        channel.basic_publish(exchange='', routing_key=rabbitmq_queue.queue_name, body=message)
        connection.close()


class SyncInfoRabbitmqNew(models.AbstractModel):
    _name = 'sync.info.rabbitmq.new'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ New'
    _new_action = 'new'

    def get_sync_new_data(self):
        ...

    def action_new_record(self):
        data = self.get_sync_new_data()
        self.push_message_to_rabbitmq(data, self._new_action)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res.sudo().with_delay(description="Create '%s'" % self._name).action_new_record()
        return res


class SyncInfoRabbitmqUpdate(models.AbstractModel):
    _name = 'sync.info.rabbitmq.update'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Update'
    _update_action = 'update'

    def get_sync_update_data(self, field_update, values):
        ...

    def action_update_record(self, field_update, values):
        data = self.get_sync_update_data(field_update, values)
        self.push_message_to_rabbitmq(data, self._update_action)

    def check_update_info(self, values):
        ...

    def write(self, values):
        res = super().write(values)
        field_update = self.check_update_info(values)
        if field_update:
            self.sudo().with_delay(description="Update '%s'" % self._name).action_update_record(field_update, values)
        return res


class SyncInfoRabbitmqRemove(models.AbstractModel):
    _name = 'sync.info.rabbitmq.remove'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Remove'
    _remove_action = 'remove'

    def action_delete_record(self, record_ids):
        data = [{'id': res_id} for res_id in record_ids]
        self.push_message_to_rabbitmq(data, self._remove_action)

    def unlink(self):
        record_ids = self.ids
        res = super().unlink()
        if record_ids:
            self.sudo().with_delay(description="Delete '%s'" % self._name).action_delete_record(record_ids)
        return res


class SyncAddressInfoRabbitmq(models.AbstractModel):
    _name = 'sync.address.info.rabbitmq'
    _inherit = ['sync.info.rabbitmq.new', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.remove']
    _description = 'Sync Address Info RabbitMQ'
    _new_action = 'new'
    _update_action = 'update'

    def get_sync_new_data(self):
        data = []
        for address in self:
            vals = {
                'id': address.id,
                'created_at': address.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': address.write_date.strftime('%Y-%m-%d %H:%M:%S'),
                'code': address.code or None,
                'name': address.name or None
            }
            data.append(vals)
        return data

    def check_update_info(self, values):
        field_check_update = ['code', 'name']
        return [item for item in field_check_update if item in values]

    def get_sync_update_data(self, field_update, values):
        map_key_rabbitmq = {
            'code': 'code',
            'name': 'name',
        }
        vals = {}
        for odoo_key in field_update:
            if map_key_rabbitmq.get(odoo_key):
                vals.update({
                    map_key_rabbitmq.get(odoo_key): values.get(odoo_key) or None
                })
        data = []
        for address in self:
            vals.update({
                'id': address.id,
                'updated_at': address.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            })
            data.append(vals)
        return data
