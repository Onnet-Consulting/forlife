# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pika
import json
import copy


class SyncInfoRabbitmqCore(models.AbstractModel):
    _name = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Core'
    _exchange = ''
    _routing_key = ''

    def get_sync_info_value(self):
        ...

    def action_sync_info_data(self, action):
        data = [line.get_sync_info_value() for line in self]
        if data:
            self.push_message_to_rabbitmq(data, action, self._name)

    def domain_record_sync_info(self):
        return self

    def get_rabbitmq_queue_by_queue_key(self, queue_key):
        rabbitmq_queue = self.env['rabbitmq.queue'].search([('queue_key', '=', queue_key)])
        if not rabbitmq_queue:
            raise ValueError(_("RabbitQM queue by key '%s' not found !") % queue_key)
        return rabbitmq_queue[0]

    def push_message_to_rabbitmq(self, data, action, queue_key):
        rabbitmq_queue = self.get_rabbitmq_queue_by_queue_key(queue_key)
        rabbitmq_connection = rabbitmq_queue.rabbitmq_connection_id
        credentials = pika.PlainCredentials(username=rabbitmq_connection.username, password=rabbitmq_connection.password)
        parameter = pika.ConnectionParameters(host=rabbitmq_connection.host, port=rabbitmq_connection.port, credentials=credentials)
        connection = pika.BlockingConnection(parameter)
        channel = connection.channel()
        message = {
            'action': action,
            'target': rabbitmq_queue.target,
            'data': data
        }
        message = json.dumps(message).encode('utf-8')
        channel.queue_declare(queue=rabbitmq_queue.queue_name, durable=True)
        if self._exchange:
            channel.exchange_declare(exchange=self._exchange, durable=True, arguments={'x-delayed-type': 'direct'})
            channel.queue_bind(queue=rabbitmq_queue.queue_name, exchange=self._exchange, routing_key=self._routing_key)
            properties = pika.BasicProperties(headers={'x-delay': 5000}, delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
            channel.basic_publish(exchange=self._exchange, routing_key=self._routing_key, body=message, properties=properties)
        else:
            channel.basic_publish(exchange='', routing_key=rabbitmq_queue.queue_name, body=message)
        connection.close()


class SyncInfoRabbitmqCreate(models.AbstractModel):
    _name = 'sync.info.rabbitmq.create'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Create'
    _create_action = 'create'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        record = res.domain_record_sync_info()
        if record:
            record.sudo().with_delay(description="Create '%s'" % self._name, channel='root.RabbitMQ').action_sync_info_data(action=self._create_action)
        return res


class SyncInfoRabbitmqUpdate(models.AbstractModel):
    _name = 'sync.info.rabbitmq.update'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Update'
    _update_action = 'update'

    def check_update_info(self, values):
        return [False, False]

    def write(self, values):
        res = super().write(values)
        check, record = self.check_update_info(values)
        if check:
            record.sudo().with_delay(description="Update '%s'" % self._name, channel='root.RabbitMQ').action_sync_info_data(action=self._update_action)
        return res


class SyncInfoRabbitmqDelete(models.AbstractModel):
    _name = 'sync.info.rabbitmq.delete'
    _inherit = 'sync.info.rabbitmq.core'
    _description = 'Sync Info RabbitMQ Delete'
    _delete_action = 'delete'

    def action_delete_record(self, record_ids):
        data = [{'id': res_id} for res_id in record_ids]
        if data:
            self.push_message_to_rabbitmq(data, self._delete_action, self._name)

    def unlink(self):
        record_ids = self.domain_record_sync_info().ids
        res = super().unlink()
        if record_ids:
            self.sudo().with_delay(description="Delete '%s'" % self._name, channel='root.RabbitMQ').action_delete_record(record_ids)
        return res


class SyncAddressInfoRabbitmq(models.AbstractModel):
    _name = 'sync.address.info.rabbitmq'
    _inherit = ['sync.info.rabbitmq.create', 'sync.info.rabbitmq.update', 'sync.info.rabbitmq.delete']
    _description = 'Sync Address Info RabbitMQ'
    _create_action = 'create'
    _update_action = 'update'

    def get_sync_info_value(self):
        self.ensure_one()
        return {
            'id': self.id,
            'created_at': self.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.write_date.strftime('%Y-%m-%d %H:%M:%S'),
            'code': self.code,
            'name': self.name
        }

    def get_sync_create_data(self):
        data = []
        for address in self:
            data.append(dict(address.get_sync_info_value()))
        return data

    def check_update_info(self, values):
        field_check_update = ['code', 'name']
        return any([field in field_check_update for field in values])
