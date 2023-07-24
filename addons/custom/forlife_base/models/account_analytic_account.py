from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    code = fields.Char('Code')
    internal_name = fields.Char('Tên nội bộ')
    address = fields.Char('Địa chỉ')

    _sql_constraints = [
        ('unique_code', 'CHECK(1 = 1)','Code must be unique!'),
        ('unique_company_code', 'UNIQUE(code, company_id)', 'Code must be unique per company !')
    ]

    def write(self, values):
        self.check_contrains(values)
        return super(AccountAnalyticAccount, self).write(values)

    @api.model_create_multi
    def create(self, vals_list):
        self.check_contrains(vals_list)
        return super(AccountAnalyticAccount, self).create(vals_list)

    def check_contrains(self, values):
        if 'code' in values and values['code']:
            company_id = int(values['company_id']) if 'company_id' in values else self.env.company.id
            code_exits = self.search([('code', '=', values['code']), ('company_id', '=', company_id)], limit=1)
            if code_exits:
                raise ValidationError('Mã tham chiếu phải là duy nhất trong từng oông ty')