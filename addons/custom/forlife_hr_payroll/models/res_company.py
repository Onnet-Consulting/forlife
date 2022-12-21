# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char(string='Code')
    salary_record_sequence_id = fields.Many2one('ir.sequence', string='Salary Record Sequence', help='Use this field to generate Name for Salary Record', ondelete="restrict")

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Company code must be unique!')
    ]
