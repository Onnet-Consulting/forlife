from odoo import api, fields, models

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    center_expense_id = fields.Many2one('account.analytic.account', required=True)
