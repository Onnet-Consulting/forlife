from odoo import api, fields, models

class DefectiveType(models.Model):
    _name = 'defective.type'

    _description = 'Defective Type'

    name = fields.Char('Loại lỗi')

    email = fields.Char('Email')

    department_id = fields.Many2one('hr.department', 'Bộ phận')
