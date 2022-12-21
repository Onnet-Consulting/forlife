# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

NUMBER_FIELDS = ["x_kq", "x_tkdp", "x_pvp", "x_tthh", "x_thl", "x_dpfm", "x_pds", "x_ttl", "x_ttpc", "x_tu", "x_tk", "x_bhxh_cn", "x_bhyt_cn", "x_bhxh_bhbnn_tnld_cn", "x_ttbh"]


class SalaryArrears(models.Model):
    _name = 'salary.arrears'
    _inherit = 'salary.general.info'
    _description = 'Salary Arrears'  # truy thu

    employee_id = fields.Many2one('hr.employee', string='Employee')
    x_kq = fields.Float(string="Ký quỹ")
    x_tkdp = fields.Float(string="TKDP")
    x_pvp = fields.Float(string="Phạt vi phạm")
    x_tthh = fields.Float(string="Trừ TTHH")
    x_thl = fields.Float(string="Trừ hàng lỗi")
    x_dpfm = fields.Float(string="Trừ đồng phục")
    x_pds = fields.Float(string="Phạt doanh số")
    x_ttl = fields.Float(string="Truy thu lương")
    x_ttpc = fields.Float(string="Truy thu phụ cấp")
    x_tu = fields.Float(string="Tạm ứng")
    x_tk = fields.Float(string="Trừ khác")
    x_bhxh_cn = fields.Float(string="Công nợ BHXH NLĐ chi trả")
    x_bhyt_cn = fields.Float(string="Công nợ BHYT NLĐ chi trả")
    x_bhxh_bhbnn_tnld_cn = fields.Float(string="Công nợ BHTN NLĐ chi trả")
    x_ttbh = fields.Float(string="Truy thu BH vào lương")
    note = fields.Text(string='Note')

    @api.constrains(*NUMBER_FIELDS)
    def _check_numbers(self):
        fields_desc = self.fields_get(NUMBER_FIELDS, ['string'])
        for rec in self:
            for num_field in NUMBER_FIELDS:
                if rec[num_field] < 0:
                    raise ValidationError(_("Field '%s' value in the table '%s' must be >= 0") % (fields_desc[num_field]['string'], self._description))

    _sql_constraints = [
        (
            'unique_info',
            'UNIQUE(salary_record_id,purpose_id,department_id,analytic_account_id,project_code,manufacture_order_code,internal_order_code, employee_id)',
            'The combination of Reference, Salary calculation purpose, Department, Cost Center, '
            'Project Code, Manufacture Order Code, Internal Order Code and Employee must be unique !'
        )
    ]
