# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import requests
import json
from datetime import timedelta
import pytz
import logging

_logger = logging.getLogger(__name__)


class ForlifeComment(models.Model):
    _name = 'forlife.comment'
    _inherit = ['action.send.message.telegram', 'odoo.app.logging']
    _description = 'Comment'
    _order = 'invoice_date desc, id desc'
    _rec_name = 'customer_code'

    question_id = fields.Integer('Question ID')
    customer_code = fields.Char('Customer Code', required=True)
    customer_name = fields.Char('Customer Name', required=True)
    store_name = fields.Char('Store Name')
    store_code = fields.Char('Store Code')
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
            line.push_notification_to_app(line.customer_code, line.brand)

    def push_notification_to_app(self, phone, brand):
        self.ensure_one()
        if self.status != -1:
            return False
        Utility = self.env['res.utility']
        try:
            link = self.env['forlife.app.api.link'].search([('key', '=', brand)], limit=1)
            if link:
                url = link.value + 'type=pushNotification&username=%s&notiId=9999' % phone
                result = requests.get(url)
                res = json.loads(result.text)
                self.sudo().write({'status': 0}) if res.get('Result', 0) else self.sudo().unlink()
                Utility.create_ir_logging(self._name, result.text, line=str(self.id), func='push_notification_to_app', path=url)
            else:
                message = f"Không tìm thấy api link với mã thương hiệu '{brand}'"
                Utility.create_ir_logging(self._name, message, line=str(self.id), func='push_notification_to_app')
        except Exception as e:
            Utility.create_ir_logging(self._name, str(e), line=str(self.id), func='push_notification_to_app')

    def remove_forlife_comment(self):
        res = self.search([('status', '=', 0), ('invoice_date', '<=', fields.Datetime.now() - timedelta(hours=24))])
        if res:
            res.sudo().unlink()

    def write(self, vals):
        res = super(ForlifeComment, self).write(vals)
        if self._context.get('update_comment', False):
            try:
                self.send_message_to_telegram()
            except Exception as e:
                _logger.error(e)
        return res

    def send_message_to_telegram(self):
        for cmt in self.filtered(lambda f: f.status == 1):
            message = 'Mã khách: %s\nTên khách: %s\nMã hóa đơn: %s\nNgày giờ: %s\nChi nhánh: %s (%s)\nMức độ(%%): %s' % (
                cmt.customer_code, cmt.customer_name, cmt.invoice_number, cmt.comment_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y %H:%M:%S'), cmt.store_name, cmt.areas, cmt.point
            )
            if cmt.comment:
                message += '\nBình luận: %s' % cmt.comment

            self.action_send_message('NPS-%s' % cmt.brand, message)
            if cmt.comment:
                self.action_send_message('NPS-%s-CSKH' % cmt.brand, message)
            self.action_send_message('%s-NPS-%s' % (cmt.brand, cmt.areas), message)
