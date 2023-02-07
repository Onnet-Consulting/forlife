# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import requests
import json
from datetime import timedelta

APP_API_LINK = {
    'TKL': 'http://app.tokyolife.vn/Api/Notification/Notification.ashx?type=pushNotification',
    'FMT': 'http://app.format.vn/Api/Notification/Notification.ashx?type=pushNotification',
}


class ForlifeComment(models.Model):
    _name = 'forlife.comment'
    _description = 'Comment'
    _order = 'status desc, id desc'
    _rec_name = 'customer_code'

    question_id = fields.Many2one('forlife.question', string='Question', required=True)
    customer_code = fields.Char('Customer Code', required=True)
    customer_name = fields.Char('Customer Name', required=True)
    branch = fields.Char('Branch')
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
    brand = fields.Char('Brand', required=True)

    def push_noti(self):
        self.status = 0

    def push_notification_to_app(self, phone, brand):
        url = APP_API_LINK.get(brand, False)
        if url:
            url += '&username=%s&notiId=9999' % phone
            result = requests.get(url)
            res = json.loads(result.text)
            self.sudo().push_noti() if res.get('Result', 0) else self.sudo().unlink()

    def remove_forlife_comment(self):
        res = self.search([('status', '=', 0), ('write_date', '<=', fields.Datetime.now() - timedelta(hours=24))])
        if res:
            res.sudo().unlink()
