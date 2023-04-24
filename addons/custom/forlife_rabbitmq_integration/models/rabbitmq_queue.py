# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class RabbitmqQueue(models.Model):
    _name = 'rabbitmq.queue'
    _description = 'Rabbitmq Queue'
    _rec_name = 'queue_name'
    _order = 'queue_name'

    model_name = fields.Char('Model Name', required=True)
    queue_name = fields.Char('Queue Name', required=True)
    description = fields.Char('Description', required=True)
    target = fields.Char('Target', required=True)
    rabbitmq_connection_id = fields.Many2one('rabbitmq.connection', 'Rabbitmq connection', required=True)

    _sql_constraints = [
        ('model_name_uniq', 'unique (model_name)', 'Model Name already exists!'),
    ]
