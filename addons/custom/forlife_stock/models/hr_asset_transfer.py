from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrAssetTransfer(models.Model):
    _name = 'hr.asset.transfer'
    _description = 'Hr Asset Transfer'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.code = fields.Char(string="Reference", default="New", copy=False)
    employee_id = fields.Many2one('hr.employee', string="User")
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id')
    note = fields.Text()
    asset_date = fields.Date(string="Create Date", default=fields.Date.context_today)
    validate_day = fields.Date(string = "Ngày xác nhận")
    cancel_day = fields.Date(string="Ngày hủy phiếu")
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_approve', 'Wait Approve'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft', copy=True)
    hr_asset_transfer_line_ids = fields.One2many('hr.asset.transfer.line', 'hr_asset_transfer_id', string="Hr Asset Transfer", copy=True)
    reject_reason = fields.Text()
    validate_date = fields.Datetime(string='Validate Date')
    cancel_date = fields.Datetime(string='Cancel Date')

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.asset.transfer.name.sequence') or 'AT'
        return super(HrAssetTransfer, self).create(vals)

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_wait_approve(self):
        for record in self:
            record.write({'state': 'wait_approve'})

    def action_approved(self):
        for record in self:
            record.write({'state': 'approved',
                          'validate_date': fields.Datetime.now()
                          })
            for item in record.hr_asset_transfer_line_ids:
                item.check_asset_code()
                item.asset_code.write({'employee': item.employee_to_id.id,
                                       'dept_code': item.account_analytic_to_id.id,
                                       'location': item.asset_location_to_id.id
                                       })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel',
                          'cancel_date': fields.Datetime.now()})
            for item in record.hr_asset_transfer_line_ids:
                item.asset_code.write({'employee': item.employee_from_id.id,
                                       'dept_code': item.account_analytic_from_id.id,
                                       'location': item.asset_location_from_id.id
                                       })


class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _description = 'Hr Asset Transfer Line'

    asset_code = fields.Many2one('assets.assets', string='Asset Code')
    employee_from_id = fields.Many2one('hr.employee', string="Employee From")
    employee_to_id = fields.Many2one('hr.employee', string="Employee To")
    account_analytic_from_id = fields.Many2one('account.analytic.account', string="Cost Center From")
    account_analytic_to_id = fields.Many2one('account.analytic.account', string="Cost Center To")
    asset_location_from_id = fields.Many2one('asset.location', string="Asset Location From")
    asset_location_to_id = fields.Many2one('asset.location', string="Asset Location To")
    hr_asset_transfer_id = fields.Many2one('hr.asset.transfer', ondelete='cascade', required=True)
    date_create = fields.Date(string='Ngày tạo',index = True, compute='_compute_date')




    @api.onchange('asset_code')
    def onchange_asset_code(self):
        if self.asset_code:
            self.employee_from_id = self.asset_code.employee.id
            self.account_analytic_from_id = self.asset_code.dept_code.id
            self.asset_location_from_id = self.asset_code.location.id

    def check_asset_code(self):
        for rec in self:
            if rec.employee_from_id.id != rec.asset_code.employee.id:
                raise ValidationError(_('Wrong value for employee. Please check again!'))
            if not rec.employee_to_id:
                raise ValidationError(_('Employee to is empty. Please check again!'))
            if rec.account_analytic_from_id.id != rec.asset_code.dept_code.id:
                raise ValidationError(_('Wrong value for account analytic. Please check again!'))
            if not rec.account_analytic_to_id:
                raise ValidationError(_('Account analytic to is empty. Please check again!'))
            if rec.asset_location_from_id.id != rec.asset_code.location.id:
                raise ValidationError(_('Wrong value for asset location. Please check again!'))
            if not rec.asset_location_to_id:
                raise ValidationError(_('Asset location to is empty. Please check again!'))
