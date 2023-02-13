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
    _inherit = 'action.send.message.telegram'
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
            line.with_delay().push_notification_to_app(line.customer_code, line.brand)

    def push_notification_to_app(self, phone, brand):
        self.ensure_one()
        if self.status != -1:
            raise ValueError('Status = %s' % self.status)
        res = self.env['forlife.app.api.link'].search([('key', '=', brand)])
        if res:
            url = res[0].value + '&username=%s&notiId=9999' % phone
            result = requests.get(url)
            res = json.loads(result.text)
            self.sudo().write({'status': 0}) if res.get('Result', 0) else self.sudo().unlink()
        else:
            raise ValueError(_("Can't find App API link with key '%s'") % brand)

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

            self.with_delay().action_send_message('NPS-%s' % cmt.brand, message)
            if cmt.comment:
                self.with_delay().action_send_message('NPS-%s-CSKH' % cmt.brand, message)
            self.with_delay().action_send_message('%s-NPS-%s' % (cmt.brand, cmt.areas), message)

    # fixme: xóa phần liên quan đến hàm btn_send_comment_from_app và action_push_notification_manual sau khi dựng xong API kết nối với App
    def btn_send_comment_from_app(self):
        ctx = dict(self._context)
        ctx.update({
            'default_comment_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Comment'),
            'res_model': 'form.update.comment',
            'target': 'new',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_net_promoter_score.form_update_comment_view_form').id, 'form']],
            'context': ctx,
        }

    def action_push_notification_manual(self):
        res = self.search([('status', '=', -1)])
        for line in res:
            line.push_notification_to_app(line.customer_code, line.brand)


class FormUpdateComment(models.TransientModel):
    _name = 'form.update.comment'
    _description = 'Form Update Comment'

    comment_id = fields.Many2one('forlife.comment', string='Comments')
    point = fields.Integer('Point', default=100)
    comment = fields.Text('Comment NPS')

    def btn_ok(self):
        self.comment_id.write({
            'point': self.point,
            'comment': self.comment,
            'comment_date': fields.Datetime.now(),
            'status': 1,
        })
