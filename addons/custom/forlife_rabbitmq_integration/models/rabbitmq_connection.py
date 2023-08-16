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
        ('unique_rabbitmq_host_info', 'UNIQUE(host, port, username)', 'The rabbitmq host info already exist !')
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

    @api.onchange('host', 'port', 'username', 'password')
    def onchange_connection_info(self):
        self.is_connected = False
        self.connection_log = False

    @api.model
    def sync_all_master_data_for_rabbitmq(self):
        queues = self.env['rabbitmq.queue'].search([('active', 'in', (True, False)), ('sync_manual', '=', True)])
        for queue in queues:
            model = self.env[queue.queue_key].sudo()
            domain = model.domain_record_sync_info()
            if queue.with_multi_company:
                companies = self.env['res.company'].search([('code', '!=', False)])
                for company in companies:
                    records = model.search(domain + [('company_id', '=', company.id)])
                    if records:
                        self._action_sync(company, records, model._name, model._priority, model._create_action)
            else:
                records = model.search(domain)
                if records:
                    self._action_sync(self.env.company, records, model._name, model._priority, model._create_action)

    @api.model
    def _action_sync(self, company, records, model_name, priority, action):
        while records:
            record = records[:min(500, len(records))]
            record.sudo().with_company(company).with_delay(
                description=f"RabbitMQ: Đồng bộ thủ công '{model_name}'", channel='root.RabbitMQ', priority=priority).action_sync_info_data(action=action)
            records = records - record
