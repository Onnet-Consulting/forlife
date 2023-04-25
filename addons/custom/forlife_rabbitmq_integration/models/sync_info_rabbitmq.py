# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pika
import json


class SyncInfoRabbitmq(models.AbstractModel):
    _name = 'sync.info.rabbitmq'
    _description = 'Sync Info RabbitMQ'

    def action_new_record(self):
        ...

    def action_update_record(self, field_update, values):
        ...

    def action_delete_record(self, record_ids):
        ...

    def check_update_info(self, values):
        ...

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

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res.sudo().with_delay(description="Create '%s'" % self._name).action_new_record()
        return res

    def write(self, values):
        res = super().write(values)
        field_update = self.check_update_info(values)
        if field_update:
            self.sudo().with_delay(description="Update '%s'" % self._name).action_update_record(field_update, values)
        return res

    def unlink(self):
        record_ids = self.ids
        res = super().unlink()
        if record_ids:
            self.sudo().with_delay(description="Delete '%s'" % self._name).action_delete_record(record_ids)
        return res
