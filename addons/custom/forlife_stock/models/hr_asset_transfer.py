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
            record.write({'state': 'approved'})
            for item in record.hr_asset_transfer_line_ids:
                item.check_product_id()
                item.product_id.write({'department_id': item.department_to_id.id})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

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
    uom_id = fields.Many2one('uom.uom', string='Uom', required=True)
    department_from_id = fields.Many2one('hr.department', string="Department From")
    department_to_id = fields.Many2one('hr.department', string="Department To")
    hr_asset_transfer_id = fields.Many2one('hr.asset.transfer', ondelete='cascade', required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.product_tmpl_id.uom_id.id
            self.department_from_id = self.product_id.department_id.id

    def check_product_id(self):
        for rec in self:
            if rec.department_from_id and rec.product_id.department_id and rec.department_from_id.id != rec.product_id.department_id.id:
                raise ValidationError(_('Wrong value for department. Please check again!'))
            if not rec.department_from_id or not rec.department_to_id:
                raise ValidationError(_('Department from or department to is empty. Please check again!'))
