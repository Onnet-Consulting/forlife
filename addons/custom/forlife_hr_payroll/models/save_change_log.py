# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime


class SaveChangeLog(models.Model):
    _name = "save.change.log"
    _description = "Save Change Log"
    _order = 'id desc'

    record = fields.Reference(selection=[('salary.record', 'salary.record')])
    name = fields.Char(string='Name', compute='_compute_record_fields')
    create_date_ref = fields.Datetime(string='Create on', compute='_compute_record_fields')
    create_user = fields.Many2one('res.users', string='Create by', compute='_compute_record_fields')
    version = fields.Integer(string='Version', compute='_compute_record_fields')
    log = fields.Char(string='Log')
    write_date_ref = fields.Datetime(string='Update on')
    write_user = fields.Many2one('res.users', string='Update by')
    company_id = fields.Many2one('res.company', string='Company_id')

    @api.depends('record')
    def _compute_record_fields(self):
        for rec in self:
            rec.name = rec.record.name if 'name' in rec.record else ''
            rec.create_date_ref = rec.record.create_date
            rec.create_user = rec.record.create_uid
            rec.version = rec.record.version if 'version' in rec.record else 0

    def create_log(self, records=False, message=''):
        records = records or False
        if not records:
            return
        for line in records:
            self.sudo().create({
                'record': '%s,%r' % (line._name, line.id),
                'log': message,
                'write_date_ref': datetime.now(),
                'write_user': self.env.uid,
                'company_id': line.company_id.id if 'company_id' in line else False,
            })
