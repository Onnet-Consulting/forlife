# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ref2 = fields.Char(string='Reference #2', copy=False)
    salary_record_id = fields.Many2one('salary.record', string='Salary record', ondelete='restrict')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_code = fields.Char(string='Project Code')
    manufacture_order_code = fields.Char(string='Manufacture Order Code')
    internal_order_code = fields.Char(string='Internal Order Code')
    # check me .