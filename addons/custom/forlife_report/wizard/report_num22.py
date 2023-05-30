# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

TITLE_LAYER1 = ['STT', 'Chi nhánh', 'Ngày', 'Số CT', 'Tổng tiền thu', 'Tổng tiền chi', 'Người tạo', 'Ngày tạo']
TITLE_LAYER2 = ['STT', 'Ngày', 'Số CT', 'Nội dung', 'Khoản mục', 'TK nợ', 'TK có', 'Số tiền thu', 'Số tiền chi', 'Tên NV', 'Mã NV']


class ReportNum22(models.TransientModel):
    _name = 'report.num22'
    _inherit = 'report.base'
    _description = 'Cash receipts report'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_ids = fields.Many2many('store', string='Store')
    so_ct = fields.Char(string='Number CT')
    type = fields.Selection([('all', _('All')), ('revenue', _('Revenue')), ('expenditure', _('Expenditure'))], 'Type', default='all', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset

        query = f"""
        """
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        # query = self._get_query()
        # self._cr.execute(query)
        # data = self._cr.dictfetchall()
        data = []
        values.update({
            'titles': TITLE_LAYER1,
            'title_layer2': TITLE_LAYER2,
            "data": data,
        })
        return values
