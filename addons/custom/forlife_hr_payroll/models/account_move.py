# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ref2 = fields.Char(string='Reference #2', copy=False)
    salary_record_id = fields.Many2one('salary.record', string='Salary record', ondelete='restrict')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_id = fields.Many2one('assets.assets', string='Project Code')
    occasion_code_id = fields.Many2one('occasion.code', string='Internal Order Code')
    expense_item_id = fields.Many2one('expense.item', string='Expense Item')
