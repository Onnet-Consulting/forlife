from odoo import api, fields, models
from odoo.exceptions import ValidationError
class OccasionCode(models.Model):
    _name = 'occasion.code'
    _rec_names_search = ['code', 'name']
    _description = 'Occasion Code'

    company_id = fields.Many2one('res.company', string='Công ty')
    name = fields.Char('Occasion name', required=True)
    group_id = fields.Many2one('occasion.group', string='Occasion group', required=True)
    code = fields.Char('Occasion code', required=True)
    is_auto_name = fields.Boolean(string='Tự sinh mã')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Mã vụ việc là duy nhất!')
    ]

    @api.onchange('is_auto_name')
    def onchange_is_auto_name(self):
        for rec in self:
            rec.set_name_by_auto()

    def set_name_by_auto(self):
        if self.is_auto_name:
            self.code = '%s%s'%(self.group_id.name, self.env['ir.sequence'].next_by_code('occasion.code.seq'))
        else:
            self.code = False

    def generation_code(self):
        pass


class OccasionGroup(models.Model):
    _name = 'occasion.group'

    _description = 'Occasion Group'

    name = fields.Char('Mã')
    description = fields.Text('Mô tả')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(name)', 'Mã nhóm phải là duy nhất!')
    ]