# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import requests
import json
from datetime import timedelta
import pytz

DATA_INFO = {
    'TKL': {
        'APP_API_LINK': 'http://app.tokyolife.vn/Api/Notification/Notification.ashx?type=pushNotification',
        'TELEGRAM_BOT_TOKEN': '687907641:AAFTlEWiFv3dYOaHyUXPbEGF-RgeeW80Ldc',
        'TELEGRAM_GROUP_ID_BY_BRAND': '-1001475374775',
        'TELEGRAM_GROUP_ID_CSKH': '-404120229',
        'TELEGRAM_GROUP_ID_BY_AREA': {
            'S1': '-377239261',
            'S2': '-365465110',
            'S3': '-371562648',
            'S4': '-366286628',
            'S5': '-658354190',
        },
    },
    'FMT': {
        'APP_API_LINK': 'http://app.format.vn/Api/Notification/Notification.ashx?type=pushNotification',
        'TELEGRAM_BOT_TOKEN': '933947687:AAFFd44GFB_RmevYiSGwYbSXrfdutrZmMyE',
        'TELEGRAM_GROUP_ID_BY_BRAND': '-1001214315278',
    },
}


class ForlifeComment(models.Model):
    _name = 'forlife.comment'
    _description = 'Comment'
    _order = 'invoice_date desc, id desc'
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

    def action_push_notification(self):
        res = self.search([('status', '=', -1), ('invoice_date', '<=', fields.Datetime.now() - timedelta(minutes=30))])
        for line in res:
            line.with_delay().push_notification_to_app(line.customer_code, line.brand)

    def push_notification_to_app(self, phone, brand):
        self.ensure_one()
        if self.status != -1:
            raise ValueError('Status = %s' % self.status)
        url = DATA_INFO.get(brand, {}).get('APP_API_LINK')
        if url:
            url += '&username=%s&notiId=9999' % phone
            result = requests.get(url)
            res = json.loads(result.text)
            self.sudo().write({'status': 0}) if res.get('Result', 0) else self.sudo().unlink()
        else:
            raise ValueError(_('App API link not found.'))

    def remove_forlife_comment(self):
        res = self.search([('status', '=', 0), ('invoice_date', '<=', fields.Datetime.now() - timedelta(hours=24))])
        if res:
            res.sudo().unlink()

    def write(self, vals):
        res = super(ForlifeComment, self).write(vals)
        if self._context.get('update_comment', False):
            self.with_delay().send_message_to_telegram()
        return res

    def send_message_to_telegram(self):
        for cmt in self.filtered(lambda f: f.status == 1):
            _data = DATA_INFO.get(cmt.brand, {})
            token = _data.get('TELEGRAM_BOT_TOKEN')
            message = 'Mã khách: %s\nTên khách: %s\nMã hóa đơn: %s\nNgày giờ: %s\nChi nhánh: %s (%s)\nMức độ(%%): %s' % (
                cmt.customer_code, cmt.customer_name, cmt.invoice_number, cmt.comment_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d-%m-%Y %H:%M:%S'), cmt.store_name, cmt.areas, cmt.point
            )
            if cmt.comment:
                message += '\nBình luận: %s' % cmt.comment

            self.env['integration.telegram'].with_delay().send_message(token, _data.get('TELEGRAM_GROUP_ID_BY_BRAND'), message)

            if _data.get('TELEGRAM_GROUP_ID_CSKH') and cmt.comment:
                self.env['integration.telegram'].with_delay().send_message(token, _data.get('TELEGRAM_GROUP_ID_CSKH'), message)

            if _data.get('TELEGRAM_GROUP_ID_BY_AREA'):
                self.env['integration.telegram'].with_delay().send_message(token, _data.get('TELEGRAM_GROUP_ID_BY_AREA').get(cmt.areas), message)
