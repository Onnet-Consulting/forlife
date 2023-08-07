# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class RabbitmqQueue(models.Model):
    _name = 'rabbitmq.queue'
    _description = 'Rabbitmq Queue'
    _rec_name = 'queue_name'
    _order = 'sequence'

    queue_key = fields.Char('Queue Key', required=True)
    queue_name = fields.Char('Queue Name', required=True)
    description = fields.Char('Description', required=True)
    target = fields.Char('Target', required=True)
    rabbitmq_connection_id = fields.Many2one('rabbitmq.connection', 'Rabbitmq connection', required=True, domain="[('is_connected', '=', True)]")
    active = fields.Boolean('Active', default=True)
    sync_manual = fields.Boolean('Sync Manual', default=False)
    sequence = fields.Integer('Sequence', default=0)

    _sql_constraints = [
        ('queue_key_uniq', 'unique (queue_key)', 'Queue Key already exists!'),
    ]
