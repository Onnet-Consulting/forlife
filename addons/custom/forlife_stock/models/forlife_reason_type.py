from odoo import api, fields, models, _


class ForlifeReasonType(models.Model):
    _name = 'forlife.reason.type'
    _description = "Forlife reason"
    _rec_name = 'name'
    _rec_names_search = ['code', 'name']

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    company_id = fields.Many2one('res.company',
                                 string='Công ty',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The code of the reason type must be unique per company!')
    ]
