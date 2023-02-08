# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import requests
import json
from datetime import timedelta

APP_API_LINK = {
    'TKL': 'http://app.tokyolife.vn/Api/Notification/Notification.ashx?type=pushNotification',
    'FMT': 'http://app.format.vn/Api/Notification/Notification.ashx?type=pushNotification',
}

BOT_TELEGRAM_TOKEN = {
    'TKL': '687907641:AAFTlEWiFv3dYOaHyUXPbEGF-RgeeW80Ldc',
    'FMT': '933947687:AAFFd44GFB_RmevYiSGwYbSXrfdutrZmMyE',
}

TELEGRAM_GROUP_ID_BY_BRAND = {
    'FMT': '-1001214315278',
    'TKL': '-1001475374775',
}

TELEGRAM_GROUP_ID_CSKH = {
    'TKL-CSKH': '-404120229',
}

TELEGRAM_GROUP_ID_BY_AREA = {
    'S1': '-377239261',
    'S2': '-365465110',
    'S3': '-371562648',
    'S4': '-366286628',
    'S5': '-658354190',
}


class ForlifeComment(models.Model):
    _name = 'forlife.comment'
    _description = 'Comment'
    _order = 'status desc, id desc'
    _rec_name = 'customer_code'

    question_id = fields.Integer('Question ID')
    customer_code = fields.Char('Customer Code', required=True)
    customer_name = fields.Char('Customer Name', required=True)
    store_name = fields.Char('Store Name')
    areas = fields.Char('Areas')
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

    def write(self, vals):
        res = super(ForlifeComment, self).write(vals)
        if self._context.get('update_comment', False):
            self.send_message_to_telegram()
        return res

    def send_message_to_telegram(self):
        for comment in self:
            token = BOT_TELEGRAM_TOKEN.get(comment.brand)

