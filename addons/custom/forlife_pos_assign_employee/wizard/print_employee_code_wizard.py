# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PrintEmployeeCodeWizard(models.TransientModel):
    _name = 'print.employee.code.wizard'
    _description = 'Print Employee Code Wizard'

    employee_code = fields.Char(required=True)
    x_employee_code = fields.Char(max=20)
    x_employee_name = fields.Char(max=60)

    def print_pdf(self):
        employee = self.env['hr.employee'].search([('code', '=', self.employee_code)], limit=1)
        if not employee:
            raise ValidationError('Mã nhân viên không tồn tại')
        res = self.env['barcode.rule'].search([('type', '=', 'employee')], order='sequence', limit=1)
        pattern = (res.pattern or 'NVBH').strip('.')
        self.update({
            'x_employee_code': f"{pattern}{self.employee_code}",
            'x_employee_name': employee.name,
        })
        return self.env['ir.actions.report']._for_xml_id('forlife_pos_assign_employee.action_print_employee_code')
