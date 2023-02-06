# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ForlifeComment(models.Model):
    _name = 'forlife.comment'
    _description = 'Comment'
    _order = 'id desc'
    _rec_name = 'customer_code'

    question_id = fields.Many2one('forlife.question', string='Question', required=True)
    customer_code = fields.Char('Customer Code', required=True)
    branch = fields.Char('Branch', required=True)
    invoice_number = fields.Char('Invoice Number', required=True)
    invoice_date = fields.Datetime('Invoice Date', required=True)
    comment_date = fields.Datetime('Comment Date')
    status = fields.Integer('Status', required=True, default=-1)
    point = fields.Integer('Point', default=0)
    comment = fields.Text('Comment')
    description = fields.Text('Description')
    is_desc = fields.Boolean('Is Desc')
    employee = fields.Char('Employee')
    type = fields.Integer('Type')
    brand = fields.Char('Brand')
