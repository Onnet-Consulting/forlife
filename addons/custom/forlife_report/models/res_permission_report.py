# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.addons.forlife_report.wizard.available_report_list import AVAILABLE_REPORT


class ResGroupReport(models.Model):
    _name = 'res.group.report'
    _description = 'Nhóm quyền báo cáo'
    _order = 'name'

    code = fields.Char('Mã quyền', required=True, default='code', copy=False)
    name = fields.Char('Tên quyền', required=True, default='name', copy=False)
    user_ids = fields.Many2many('res.users', 'res_group_report_users_rel', string='Người dùng', copy=False)
    data_permission_ids = fields.Many2many('res.field.report', 'res_group_report_field_rel', string='Quyền dữ liệu', copy=False)

    _sql_constraints = [
        ("group_uniq", "unique(code, name)", "Tổ hợp (Mã quyền và Tên quyền) đã tồn tại")
    ]


class ResFieldReport(models.Model):
    _name = 'res.field.report'
    _description = 'Trường dữ liệu được phân quyền'
    _order = 'report, id desc'

    @api.model
    def _get_report_selection(self):
        return [(k, v.get('name')) for k, v in AVAILABLE_REPORT.items()]

    name = fields.Char('Mã định danh', required=True)
    report = fields.Selection(string='Báo cáo', selection=_get_report_selection, required=True)
    field_id = fields.Many2one('ir.model.fields', string='Trường dữ liệu', required=False, ondelete='cascade', copy=False)
    value_ids = fields.Many2many('res.field.value.report', 'res_field_report_value_rel', string='Dữ liệu', copy=False)

    _sql_constraints = [
        ("field_uniq", "unique(name, report, field_id)", "Tổ hợp (Mã định danh, Báo cáo, Trường dữ liệu) đã tồn tại")
    ]

    @api.onchange('report')
    def onchange_report(self):
        self.field_id = False

    def reset_all_value(self):
        self.value_ids = [(5, 0, 0)]


class ResFieldValueReport(models.Model):
    _name = 'res.field.value.report'
    _description = 'Dữ liệu chi tiết'
    _order = 'name'

    name = fields.Char('Giá trị dữ liệu', required=True)
    description = fields.Char('Mô tả')

    _sql_constraints = [
        ("value_uniq", "unique(name)", "Giá trị dữ liệu đã tồn tại")
    ]
