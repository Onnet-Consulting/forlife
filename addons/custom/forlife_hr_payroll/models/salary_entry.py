# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SalaryEntry(models.Model):
    _name = 'salary.entry'
    _description = 'Salary Entry'  # khoản mục
    _rec_name = 'show_name'

    salary_table_id = fields.Many2one('ir.model',
                                      domain="[('model', 'in', ['salary.record.main', 'salary.total.income', 'salary.supplementary', 'salary.arrears'])]",
                                      string='Table', required=True, ondelete="cascade")
    salary_field_id = fields.Many2one('ir.model.fields', required=True, string='Field',
                                      domain="[('model_id', '=', salary_table_id)]", ondelete="cascade")
    title = fields.Char(string='Title', required=True)
    show_name = fields.Char(compute='_compute_show_name', store=True, string='Name')
    groupable_account_ids = fields.Many2many('account.account', string='Groupable Accounts', check_company=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    expense_item_id = fields.Many2one('expense.item', string='Expense Item')

    @api.depends('salary_table_id', 'salary_field_id')
    def _compute_show_name(self):
        for rec in self:
            rec.show_name = '%s-%s' % (rec.salary_table_id.name, rec.salary_field_id.field_description)

    @api.onchange('salary_table_id')
    def _onchange_salary_table(self):
        self.salary_field_id = False

    @api.constrains('salary_table_id', 'salary_field_id')
    def _check_field_and_table(self):
        for record in self:
            if record.salary_field_id.model_id != record.salary_table_id:
                raise ValidationError(_("Field %s must belong to the Table %s") % (
                record.salary_field_id.name, record.salary_table_id.name))

    _sql_constraints = [
        ('unique_combination', 'UNIQUE(salary_field_id, salary_table_id, company_id)',
         'The combination of Field and Table must be unique !')
    ]
