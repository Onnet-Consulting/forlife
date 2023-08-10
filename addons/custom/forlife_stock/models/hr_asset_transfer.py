from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrAssetTransfer(models.Model):
    _name = 'hr.asset.transfer'
    _description = 'Hr Asset Transfer'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    name = fields.code = fields.Char(string="Reference", default="New", copy=False)
    employee_id = fields.Many2one('hr.employee', string="User")
    user_id = fields.Many2one('res.users', string='Người tạo', default=lambda self: self.env.user.id)
    department_id = fields.Many2one('hr.department', string="Department", related='user_id.department_default_id')
    note = fields.Text()
    asset_date = fields.Date(string="Create Date", default=fields.Date.context_today)
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_approve', 'Wait Approve'),
                   ('approved_out', 'Xác nhận xuất'),
                   ('approved_in', 'Xác nhận nhập'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft', copy=False)
    hr_asset_transfer_line_ids = fields.One2many('hr.asset.transfer.line', 'hr_asset_transfer_id', string="Hr Asset Transfer", copy=True)
    reject_reason = fields.Text()
    validate_date = fields.Datetime(string='Validate Date')
    cancel_date = fields.Datetime(string='Cancel Date')
    location_id = fields.Many2one('stock.location', string='Kho xuất', check_company=True)
    location_dest_id = fields.Many2one('stock.location', string='Kho nhập', check_company=True)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.asset.transfer.name.sequence') or 'AT'
        return super(HrAssetTransfer, self).create(vals_list)

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_wait_approve(self):
        for record in self:
            for item in record.hr_asset_transfer_line_ids:
                item.check_asset_code()
            record.write({'state': 'wait_approve'})

    def action_approved(self):
        for record in self:
            state = 'wait_approve'
            if record.state == 'wait_approve':
                state = 'approved_out'
            if record.state == 'approved_out':
                state = 'approved_in'
            record.write({
                'state': state,
                'validate_date': fields.Datetime.now()
            })
            for item in record.hr_asset_transfer_line_ids:
                item.asset_code.write({
                    'employee': item.employee_to_id.id,
                    'dept_code': item.account_analytic_to_id.id,
                    'location': item.asset_location_to_id.id
                })

    def action_cancel(self):
        for record in self:
            record.write({
                'state': 'cancel',
                'cancel_date': fields.Datetime.now()
            })
            for item in record.hr_asset_transfer_line_ids:
                item.asset_code.write({
                    'employee': item.employee_from_id.id,
                    'dept_code': item.account_analytic_from_id.id,
                    'location': item.asset_location_from_id.id
                })


class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _description = 'Hr Asset Transfer Line'

    company_id = fields.Many2one('res.company', related='hr_asset_transfer_id.company_id')

    asset_code = fields.Many2one('assets.assets', string='Tài sản')
    asset_code_code = fields.Char(related='asset_code.code', string='Mã tài sản')
    employee_from_id = fields.Many2one('hr.employee', string="Employee From")
    employee_to_id = fields.Many2one('hr.employee', string="Employee To")
    account_analytic_from_id = fields.Many2one('account.analytic.account', string="Cost Center From", related='asset_code.dept_code', store=True)
    account_analytic_to_id = fields.Many2one('account.analytic.account', string="Cost Center To")
    asset_location_from_id = fields.Many2one('asset.location', string="Asset Location From", related='asset_code.location', store=True)
    asset_location_to_id = fields.Many2one('asset.location', string="Asset Location To")
    hr_asset_transfer_id = fields.Many2one('hr.asset.transfer', ondelete='cascade', required=True)
    check_required = fields.Boolean(compute='compute_check_required')
    quantity = fields.Integer(related='asset_code.quantity', string='Số lượng')
    redundant = fields.Integer(string='Số lượng thừa')
    lack = fields.Integer(string='Số lượng thiếu')

    @api.depends('employee_to_id', 'account_analytic_to_id', 'asset_location_to_id')
    def compute_check_required(self):
        for item in self:
            if item.employee_to_id or item.account_analytic_to_id or item.asset_location_to_id:
                item.check_required = True
            else:
                item.check_required = False

    # @api.onchange('asset_code')
    # def onchange_asset_code(self):
    #     if self.asset_code:
    #         self.employee_from_id = self.asset_code.employee.id
    #         self.account_analytic_from_id = self.asset_code.dept_code.id
    #         self.asset_location_from_id = self.asset_code.location.id

    def check_asset_code(self):
        for rec in self:
            if rec.employee_from_id.id != rec.asset_code.employee.id:
                raise ValidationError(_('Wrong value for employee. Please check again!'))
            if rec.account_analytic_from_id.id != rec.asset_code.dept_code.id:
                raise ValidationError(_('Wrong value for account analytic. Please check again!'))
            if rec.asset_location_from_id.id != rec.asset_code.location.id:
                raise ValidationError(_('Wrong value for asset location. Please check again!'))
            if not rec.check_required:
                raise ValidationError(_('Nhập 1 trong các trường thông tin bắt buộc: Nhân viên, Địa điểm, Trung tâm chi phí!'))
