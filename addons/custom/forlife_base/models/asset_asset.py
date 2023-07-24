from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class AssetsAssets(models.Model):
    _name = 'assets.assets'
    _description = 'Assets'

    type = fields.Selection([('CCDC', 'CCDC'), ('TSCD', 'TSCD'), ('XDCB', 'XDCB')], string='Type')
    code = fields.Char('Code', size=24, required=True)
    state = fields.Selection([('using','Đang sử dụng'),('paid','Đã thanh lí')], string='Trạng thái')
    card_no = fields.Char('CardNo', size=24)
    item_code = fields.Char('ItemCode', size=24)
    name = fields.Char('Name', size=192)
    company_id = fields.Many2one('res.company', string='Company')
    location = fields.Many2one('asset.location', string='Location')
    unit = fields.Char(string='Unit', size=8)
    capacity = fields.Char('Capacity', size=64)
    made_year = fields.Integer('Made Year')
    made_in = fields.Char('Made in', size=64)
    asset_account = fields.Many2one('account.account', 'Asset Account')
    use_ful_month = fields.Integer('UseFul month')
    doc_date = fields.Date('Doc Date')
    original_cost = fields.Float('Original Cost')
    depr_debit_account = fields.Many2one('account.account', string='Depr Debit Account')
    depr_credit_account = fields.Many2one('account.account', string='Depr Credit Account')
    dept_code = fields.Many2one('account.analytic.account', string='Dept Code')
    comment = fields.Text('Comment')
    quantity = fields.Integer('Quantity')
    employee = fields.Many2one('hr.employee', string='Employee')
    category_product = fields.Many2one('product.category',string='Danh mục sản phẩm', domain=[('asset_group','=',True)])

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 'Mã nhóm phải là duy nhất trong cùng một công ty!')
    ]

    def write(self, values):
        if not self._context.get('from_bravo'):
            self.check_type(values)
        return super(AssetsAssets, self).write(values)

    @api.model_create_multi
    def create(self, vals):
        if not self._context.get('from_bravo'):
            self.check_type(vals)
        return super(AssetsAssets, self).create(vals)

    def check_type(self,vals):
        if 'type' in vals and (vals['type'] == "CCDC" or vals['type'] == "TSCD"):
            raise ValidationError('Không được phép tạo tài sản từ odoo')
