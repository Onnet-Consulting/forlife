# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import pika


class RabbitmqConnection(models.Model):
    _name = 'rabbitmq.connection'
    _description = 'Rabbitmq Connection'
    _rec_name = 'host'

    host = fields.Char('Host', required=True, default='localhost')
    port = fields.Char('Port', default='5672')
    username = fields.Char('Username', required=True)
    password = fields.Char('Password', required=True)
    is_connected = fields.Boolean('Is Connected', default=False)
    connection_log = fields.Text("Connection log")

    _sql_constraints = [
        ('unique_rabbitmq_host_info', 'UNIQUE(host, port, username)', 'The rabbitmq host info must be unique !')
    ]

    def name_get(self):
        res = []
        for rabbitmq in self:
            name = f'{rabbitmq.host}:{rabbitmq.port}/{rabbitmq.username}'
            res.append((rabbitmq.id, name))
        return res

    def test_rabbitmq_connection(self):
        try:
            credentials = pika.PlainCredentials(username=self.username, password=self.password)
            parameter = pika.ConnectionParameters(host=self.host, port=self.port, credentials=credentials)
            connection = pika.BlockingConnection(parameter)
            connection.close()
            self.write({
                'connection_log': _('Succeeded'),
                'is_connected': True,
            })
        except Exception as exc:
            self.write({
                'connection_log': str(exc) or str(exc.args),
                'is_connected': False,
            })
