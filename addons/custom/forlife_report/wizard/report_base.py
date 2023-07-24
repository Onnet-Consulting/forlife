# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.forlife_report.wizard.available_report_list import AVAILABLE_REPORT

from pytz import timezone
from datetime import datetime
import base64
import re
from odoo.tools.misc import xlsxwriter
import io


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
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        replace_list = set(re.findall(r'\d\.\d', data))
        for r in replace_list:
            data = data.replace(r, r[0] + r[2])
        formats = self.get_format_workbook(workbook)
        final_data = data.split('\n')
        sheet = workbook.add_worksheet('data')
        sheet.set_row(0, 25)
        row = 0
        for vals in final_data:
            col = 0
            for val in vals.split('\t'):
                if row == 0:
                    sheet.write(row, col, val, formats.get('title_format'))
                else:
                    sheet.write(row, col, val, formats.get('normal_format'))
                col += 1
            row += 1
        workbook.close()
        output.seek(0)
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'datas': base64.encodebytes(output.read()),
        })
        output.close()
        return {
            'type': 'ir.actions.act_url',
            'url': f"web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&name={attachment_id.name}&download=true",
            'target': 'new',
        }
