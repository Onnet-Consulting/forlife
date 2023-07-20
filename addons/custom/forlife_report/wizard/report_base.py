# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.forlife_report.wizard.available_report_list import AVAILABLE_REPORT

from pytz import timezone
from datetime import datetime
import base64
import json


def format_date_query(column_name, tz_offset):
    """
    Because DB save datetime value in UTC timezone, so
    when we compare a 'datetime' value with a 'date' value,
    we must convert datetime value to date value by adding a 'tz_offset'
    @param column_name: str - original column name
    @param tz_offset: int - timezone offset (seconds)
    @return : str - formatted column name with date conversion
    """
    return f"""to_date(to_char({column_name} + interval '{tz_offset} hours', 'YYYY-MM-DD'), 'YYYY-MM-DD')"""


class ReportBase(models.AbstractModel):
    _inherit = 'report.base'

    @api.model
    def get_default_name(self):
        return AVAILABLE_REPORT.get(self._name, {}).get('name', '')

    tz = fields.Selection(_tz_get, default="Asia/Ho_Chi_Minh", string="Timezone",
                          help='Timezone used for selecting datetime data from DB', required=True)
    tz_offset = fields.Integer(compute='_compute_timezone_offset', string="Timezone offset",
                               help='Timezone offset in hours')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    name = fields.Char(default=get_default_name)

    @api.depends('tz')
    def _compute_timezone_offset(self):
        for rec in self:
            localize_now = datetime.now(timezone(self.tz))
            rec.tz_offset = int(localize_now.utcoffset().total_seconds() / 3600)

    @api.model
    def get_available_report(self):
        res = []
        for k, v in AVAILABLE_REPORT.items():
            val = dict(v)
            val.update({'do_action': f'forlife_report.{k.replace(".", "_")}_window_action'})
            res.extend([val])
        return res

    def get_data(self, allowed_company):
        report_data = AVAILABLE_REPORT.get(self._name, {})
        return {
            'reportTitle': report_data.get('name', ''),
            'reportTemplate': report_data.get('reportTemplate', ''),
            'reportPager': report_data.get('reportPager', False),
            'recordPerPage': 80 if report_data.get('reportPager', False) else False,
        }

    def view_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': AVAILABLE_REPORT.get(self._name, {}).get('tag', 'report_base_action'),
            'context': {
                'report_model': self._name,
            },
            'params': {'active_model': self._name},
        }


class ReportCategoryType(models.AbstractModel):
    _name = 'report.category.type'
    _description = 'Category Type Relate'

    category_type_id = fields.Many2one('product.category.type', string="Type of Product Category")
    product_brand_id = fields.Many2one('product.category', 'Level 1')

    @api.onchange('category_type_id')
    def onchange_category_type(self):
        self.product_brand_id = self.product_brand_id.filtered(lambda f: f.category_type_id in self.category_type_id)


class ExportExcelClient(models.AbstractModel):
    _name = 'export.excel.client'
    _description = 'Export excel from client'

    @api.model
    def export_excel_from_client(self, data, filename):
        data = json.dumps(data).encode('utf-8')
        base64_bytes = base64.b64encode(data)
        base64_string = base64_bytes.decode("utf-8")
        return {
            'type': 'ir.actions.act_url',
            'name': self._description,
            'url': f'/client/download/xlsx?model_name={self._name}&data={base64_string}&filename={filename}',
            'target': 'current',
        }
