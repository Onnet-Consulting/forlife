from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import re
import base64
import xlsxwriter
from io import BytesIO

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Request"

    name = fields.Char(string="Request name", required=True, default='New', copy=False)
    # wo_code = fields.Char(string="Work Order Code")
    user_id = fields.Many2one('res.users', string="User Requested", required=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string='User Request', required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    date_planned = fields.Datetime(string='Expected Arrival', required=True)
    request_date = fields.Date(string='Request date', default=lambda self: fields.Date.context_today(self))
    order_lines = fields.One2many('purchase.request.line', 'request_id', copy=True)
    order_ids = fields.One2many('purchase.order', 'request_id')
    rejection_reason = fields.Char(string="Rejection_reason")

    state = fields.Selection(
        copy=False,
        default='draft',
        string="Status",
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('close', 'Close'),
                   ], tracking=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company.id)
    approval_logs_ids = fields.One2many('approval.logs', 'purchase_request_id')



    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            if 'employee_id' not in fields or 'department_id' not in fields or 'request_date' not in fields:
                raise ValidationError(_("The import file must contain the required column"))
        return super().load(fields, data)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['department_id'] = self.env.user.department_id.id if self.env.user.department_id else False
        return res

    def submit_action(self):
        for record in self:
            record.write({'state': 'confirm'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def approve_action(self):
        # template_id = self.env.ref('purchase_request.approve_purchase_email_template').id
        # template = self.env['mail.template'].browse(template_id)
        # category = self.env.ref('base.module_category_inventory_purchase', raise_if_not_found=False)
        # users = self.env['res.groups'].search([('category_id', '=', category.id)]).users
        # for u in users:
        #     if u.id != self._uid:
        #         template.write({'email_to': u.id})
        # template.send_mail(self.id, force_send=True)
        for rec in self:
            rec.write({
                'approval_logs_ids': [(0, 0, {
                    'res_model': rec._name,
                    'request_approved_date': date.today(),
                    'approval_user_id': rec.env.user.id,
                    'note': 'Approve',
                    'state': 'approved',
                })],
            })
        self.write({'state': 'approved'})

    def close_action(self):
        for record in self:
            record.write({'state': 'close'})

    def set_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Download Template for Purchase Request'),
            'template': '/purchase_request/static/src/xlsx/template_pr.xlsx?download=true'
        }]

    def orders_smart_button(self):
        return {
            'name': 'Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('purchase_request_ids', '=', self.id)],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.name.sequence') or 'Pr'
        return super(PurchaseRequest, self).create(vals)

    def action_create_purchase_order(self):
        for r in self:
            list_consumable = []
            list_service = []
            list_product = []
            # for line in r.order_lines:
            #     if line.product_id.detailed_type == 'consu' and r.state == 'approved':
            #         list_consumable.append(line.product_id.id)
            #         r.state = 'sale'
            #     elif line.product_id.detailed_type == 'service' and r.state == 'approved':
            #         list_service.append(line.product_id.id)
            #         r.state = 'sale'
            #     else:
            #         list_product.append(line.product_id.id)
            #         r.state = 'sale'
            # if list_consumable:
            #     for item in list_consumable:
            #         self.env['purchase.order'].create({
            #             'product_id': item,
            #             'state': 'purchase'
            #         })

    @api.constrains('order_lines')
    def constrains_order_lines(self):
        if not self.order_lines:
            raise ValidationError(
                _('It is mandatory to enter all the commodity information before confirming the purchase request!'))

    def unlink(self):
        if any(item.state not in ('draft', 'cancel') for item in self):
            raise ValidationError("You only delete a record in draft and cancel status")
        return super(PurchaseRequest, self).unlink()

    def create_purchase_orders(self):
        order_lines_ids = self.filtered(lambda r: r.state != 'close').order_lines.ids
        order_lines_groups = self.env['purchase.request.line'].read_group(domain=[('id', 'in', order_lines_ids)],
                                    fields=['product_id', 'vendor_code', 'product_type'],
                                    groupby=['vendor_code', 'product_type'], lazy=False)
        purchase_order = self.env['purchase.order']
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError('Chỉ tạo được đơn hàng mua với các phiếu yêu cầu mua hàng có trạng thái Approved!')
        for group in order_lines_groups:
            domain = group['__domain']
            vendor_code = group['vendor_code']
            product_type = group['product_type']
            vendor_id = vendor_code[0] if vendor_code else False
            purchase_request_lines = self.env['purchase.request.line'].search(domain)
            po_line_data = []
            for line in purchase_request_lines:
                if line.is_no_more_quantity:
                    continue
                po_line_data.append((0, 0, {
                    'purchase_request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'purchase_quantity': line.purchase_quantity - line.order_quantity,
                    'exchange_quantity': line.exchange_quantity,
                    'product_qty': (line.purchase_quantity - line.order_quantity) * line.exchange_quantity,
                    # 'product_uom': line.purchase_uom.id,
                    'purchase_uom': line.purchase_uom.id,
                }))
            if po_line_data:
                po_data = {
                    'partner_id': vendor_id,
                    'purchase_type': product_type,
                    'purchase_request_ids': [(6, 0, purchase_request_lines.mapped('request_id').ids)],
                    'order_line': po_line_data,
                }
                purchase_order |= purchase_order.create(po_data)
        if not purchase_order:
            raise ValidationError('Sản phẩm đã được lấy hết!')

        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_order.ids)],
        }

    is_no_more_quantity = fields.Boolean(compute='_compute_is_no_more_quantity', store=1)

    @api.depends('order_lines', 'order_lines.is_no_more_quantity')
    def _compute_is_no_more_quantity(self):
        for rec in self:
            rec.is_no_more_quantity = all(rec.order_lines.mapped('is_no_more_quantity'))

    @api.constrains('request_date', 'date_planned')
    def constrains_request_date(self):
        for item in self:
            if item.request_date > item.date_planned.date():
                raise ValidationError(_("Expected Arrival must be greater than request date"))


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_type = fields.Selection(related='product_id.detailed_type', string='Type', store=1)
    asset_description = fields.Char(string="Asset description")
    description = fields.Char(string="Description", store=1)
    vendor_code = fields.Many2one('res.partner', string="Vendor")
    production_id = fields.Many2one('forlife.production', string='Production Order Code')
    request_id = fields.Many2one('purchase.request')
    date_planned = fields.Datetime(string='Expected Arrival')
    request_date = fields.Date(string='Request date')
    purchase_quantity = fields.Integer('Quantity Purchase', digits='Product Unit of Measure')
    purchase_uom = fields.Many2one('uom.uom', string='UOM Purchase')
    exchange_quantity = fields.Float('Exchange Quantity')
    purchase_order_line_ids = fields.One2many('purchase.order.line', 'purchase_request_line_id')
    order_quantity = fields.Integer('Quantity Order', compute='_compute_order_quantity', store=1)
    is_no_more_quantity = fields.Boolean(compute='_compute_is_no_more_quantity', store=1)
    state = fields.Selection(
        string="Status",
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('close', 'Close'),
                   ])

    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.state')
    def _compute_order_quantity(self):
        for rec in self:
            done_purchase_order_line = rec.purchase_order_line_ids.filtered(lambda r: r.state == 'purchase')
            rec.order_quantity = sum(done_purchase_order_line.mapped('product_qty'))

    @api.depends('purchase_quantity', 'order_quantity')
    def _compute_is_no_more_quantity(self):
        for rec in self:
            rec.is_no_more_quantity = rec.purchase_quantity == rec.order_quantity

    @api.constrains('purchase_quantity')
    def constrains_purchase_quantity(self):
        for item in self:
            if item.purchase_quantity <= 0:
                raise ValidationError("Quantity purchase must be greater than 0!")

    @api.constrains('exchange_quantity')
    def _constraint_unique(self):
        for rec in self:
            if rec.exchange_quantity <= 0:
                raise ValidationError('Exchange quantity must be greater than 0 !')


class ApprovalLogs(models.Model):
    _name = 'approval.logs'
    _description = 'Approval Logs'

    purchase_request_id = fields.Many2one('purchase.request', ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', ondelete='cascade')
    res_model = fields.Char('Resource Model')
    request_approved_date = fields.Date('Request Approved', default=fields.Date.context_today)
    approval_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    function = fields.Char(related='approval_user_id.function')  # Job Position in res.user
    note = fields.Text()
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('close', 'Close'),
                   ])
