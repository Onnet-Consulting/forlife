from odoo import api, fields, models

class OccasionCode(models.Model):
    _name = 'occasion.code'
    _rec_names_search = ['code', 'name']
    _description = 'Occasion Code'

    company_id = fields.Many2one('res.company', string='Công ty')
    name = fields.Char('Occasion name')
    group_id = fields.Many2one('occasion.group', string='Occasion group')
    code = fields.Char('Occasion code', readonly=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Mã vụ việc là duy nhất!')
    ]

    @api.model_create_single
    def create(self, vals_list):
        res = super().create(vals_list)
        res.code = '%s%s'%(res.group_id.name, self.env['ir.sequence'].next_by_code('occasion.code.seq'))
        return res


class OccasionGroup(models.Model):
    _name = 'occasion.group'

    _description = 'Occasion Group'

    name = fields.Char('Mã')
    description = fields.Text('Mô tả')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(name)', 'Mã nhóm phải là duy nhất!')
    ]