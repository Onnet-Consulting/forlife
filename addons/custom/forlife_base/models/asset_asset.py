from odoo import api, fields, models


class AssetsAssets(models.Model):
    _name = 'assets.assets'

    type = fields.Selection([('CCDC', '0'), ('TSCD', '1')], string='Type')
    code = fields.Char('Code', size=24)
    card_no = fields.Char('CardNo', size=24)
    item_code = fields.Char('ItemCode', size=24)
    name = fields.Char('Name', size=192)
    company_id = fields.Many2one('res.company', string='Company')
    location = fields.Many2one('asset.location',string='Location')
    unit = fields.Char(string='Unit', size=8)
    capacity = fields.Char('Capacity', size=64)
    made_year = fields.Integer('Made Year')
    made_in = fields.Char('Made in', size=64)
    asset_account = fields.Char('Asset Account', size=24)
    use_ful_month = fields.Integer('UseFul month')
    doc_date = fields.Date('Doc Date')
    original_cost = fields.Float('Original Cost')
    depr_debit_account = fields.Char(size=24, string='Depr Debit Account')
    depr_credit_account = fields.Char(size=24, string='Depr Credit Account')
    dept_code = fields.Many2one('account.analytic.account',string='Dept Code')
    comment = fields.Text('Comment')
    quantity = fields.Integer('Quantity')
    employee = fields.Many2one('hr.employee', string='Employee')
    elavation_group_1 = fields.Char(string='Elavation group 1')
    elavation_group_2 = fields.Char(string='Elavation group 2')
    elavation_group_3 = fields.Char(string='Elavation group 3')
    push_date = fields.Datetime(string='Push Date')
