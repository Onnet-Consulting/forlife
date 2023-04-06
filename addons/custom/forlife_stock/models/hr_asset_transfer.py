from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrAssetTransfer(models.Model):
    _name = 'hr.asset.transfer'
    _description = 'Hr Asset Transfer'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.code = fields.Char(string="Reference", default="New", copy=False)
    employee_id = fields.Many2one('hr.employee', string="User")
    department_id = fields.Many2one('hr.department', string="Department")
    note = fields.Text()
    asset_date = fields.Date(string="Create Date", default=fields.Date.context_today)
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_approve', 'Wait Approve'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft', copy=True)
    hr_asset_transfer_line_ids = fields.One2many('hr.asset.transfer.line', 'hr_asset_transfer_id', string="Hr Asset Transfer", copy=True)
    selected_product_ids = fields.Many2many('product.product', string='Selected Products', compute='compute_product_id')
    reject_reason = fields.Text()
    validate_date = fields.Datetime(string='Ngày cập nhật')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['department_id'] = self.env.user.department_id.id if self.env.user.department_id else False
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
                item.check_product_id()
                item.product_id.write({'department_id': item.department_to_id.id,
                                       'employee_id': item.employee_to_id.id,
                                       'account_analytic_id': item.account_analytic_to_id.id,
                                       'asset_location_id': item.asset_location_to_id.id
                                       })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel',
                          'validate_date': fields.Datetime.now()})
            for item in record.hr_asset_transfer_line_ids:
                item.product_id.write({'department_id': item.department_from_id.id,
                                       'employee_id': item.employee_from_id.id,
                                       'account_analytic_id': item.account_analytic_from_id.id,
                                       'asset_location_id': item.asset_location_from_id.id
                                       })

    @api.depends('hr_asset_transfer_line_ids')
    def compute_product_id(self):
        for rec in self:
            if rec.hr_asset_transfer_line_ids:
                self.selected_product_ids = [(6, 0, [item.product_id.id for item in rec.hr_asset_transfer_line_ids if item.product_id])]
            else:
                self.selected_product_ids = False


class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _description = 'Hr Asset Transfer Line'

    product_id = fields.Many2one('product.product', 'Product', required=True)
    asset_tag = fields.Char(string='Asset Tag')
    uom_id = fields.Many2one(related="product_id.uom_id", string='Uom')
    department_from_id = fields.Many2one('hr.department', string="Department From")
    department_to_id = fields.Many2one('hr.department', string="Department To")
    employee_from_id = fields.Many2one('hr.employee', string="Employee From")
    employee_to_id = fields.Many2one('hr.employee', string="Employee To")
    account_analytic_from_id = fields.Many2one('account.analytic.account', string="Cost Center From")
    account_analytic_to_id = fields.Many2one('account.analytic.account', string="Cost Center To")
    asset_location_from_id = fields.Many2one('asset.location', string="Asset Location From")
    asset_location_to_id = fields.Many2one('asset.location', string="Asset Location To")
    hr_asset_transfer_id = fields.Many2one('hr.asset.transfer', ondelete='cascade', required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.product_tmpl_id.uom_id.id
            self.department_from_id = self.product_id.department_id.id
            self.employee_from_id = self.product_id.employee_id.id
            self.account_analytic_from_id = self.product_id.account_analytic_id.id
            self.asset_location_from_id = self.product_id.asset_location_id.id

    def check_product_id(self):
        for rec in self:
            if rec.employee_from_id and rec.product_id.employee_id and rec.employee_from_id.id != rec.product_id.employee_id.id:
                raise ValidationError(_('Wrong value for employee. Please check again!'))
            if not rec.employee_to_id:
                raise ValidationError(_('Employee to is empty. Please check again!'))
            if rec.account_analytic_from_id and rec.product_id.account_analytic_id and rec.account_analytic_from_id.id != rec.product_id.account_analytic_id.id:
                raise ValidationError(_('Wrong value for account analytic. Please check again!'))
            if not rec.account_analytic_to_id:
                raise ValidationError(_('Account analytic to is empty. Please check again!'))
            if rec.asset_location_from_id and rec.product_id.asset_location_id and rec.asset_location_from_id.id != rec.product_id.asset_location_id.id:
                raise ValidationError(_('Wrong value for asset location. Please check again!'))
            if not rec.asset_location_to_id:
                raise ValidationError(_('Asset location to is empty. Please check again!'))
