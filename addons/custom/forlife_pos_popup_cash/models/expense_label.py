from odoo import api, fields, models


class ExpenseLabel(models.Model):
    _name = 'pos.expense.label'
    _description = 'POS Expense Label'
    _rec_names_search = ['code', 'name']

    code = fields.Char('Code', required=True)
    name = fields.Char('Description', required=True)

    def name_get(self):
        result = []
        for label in self:
            result.append((label.id, label.code + ' - ' + label.name))
        return result
