# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz


class NetPromoterScoreReport(models.TransientModel):
    _name = 'net.promoter.score.report'
    _description = 'Net Promoter Score Report'

    name = fields.Char('Name', default='.')
    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    customer_code = fields.Text('Customer Code')
    invoice_number = fields.Text('Invoice Number')
    min_point = fields.Integer('Min Point', default=0)
    max_point = fields.Integer('Max Point', default=100)
    view_report = fields.Html('View Report')

    def btn_search(self):
        domain = [('status', '=', '1')]
        if self.from_date:
            domain += [('invoice_date', '>=', self.from_date)]
        if self.to_date:
            domain += [('invoice_date', '<=', self.to_date)]
        if self.customer_code:
            domain += [('customer_code', 'in', [i.strip() for i in self.customer_code.split(',')])]
        if self.invoice_number:
            domain += [('invoice_number', 'in', [i.strip() for i in self.invoice_number.split(',')])]
        result = self.env['forlife.comment'].search(domain)
        data = ''
        stt = 1
        for line in result:
            style = ' style="background: #0a0a0a3d;"' if stt % 2 == 0 else ''
            val = [line.store_name, line.customer_code, line.customer_name, line.invoice_number,
                   line.invoice_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d-%m-%Y'),
                   line.comment_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d-%m-%Y') if line.comment_date else '',
                   str(line.point), line.comment or '', str(line.status)]
            data += f'<tr{style}><td style="text-align: center;">{str(stt)}</td><td>{"</td><td>".join(val)}</td></tr>'
            stt += 1
        header = ['STT', 'Chi nhánh', 'Mã KH', 'Tên KH', 'Mã HĐ', 'Ngày mua hàng', 'Ngày đánh giá', 'Đánh giá', 'Bình luận', 'Trạng thái']
        self.view_report = f'<table class="table table-bordered"><tr style="text-align: center; background: #031d74c7; color: #ffffff;">' \
                           f'<th>{"</th><th>".join(header)}</th></tr>{data}</table>'

    @api.constrains("start_date", "finish_date")
    def validate_point(self):
        for record in self:
            if record.min_point < 0 or record.max_point > 100 or record.min_point > record.max_point:
                raise ValidationError(_('Invalid Level.'))
