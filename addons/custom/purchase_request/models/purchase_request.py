from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import base64
import xlsxwriter
from io import BytesIO

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Request"

    name = fields.Char(string="Request name", required=True, default='New', copy=False)
    user_id = fields.Many2one('res.users', string="User Requested", required=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string='User Request', required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    date_planned = fields.Datetime(string='Expected Arrival', required=True,  widget='datetime', options={'format': 'DD-MM-YYYY HH:mm:ss'})
    request_date = fields.Date(string='Request date', default=lambda self: fields.Date.context_today(self), required=True, options={'format': 'DD-MM-YYYY'})
    order_lines = fields.One2many('purchase.request.line', 'request_id', copy=True)
    order_ids = fields.One2many('purchase.order', 'request_id')
    rejection_reason = fields.Char(string="Rejection_reason")
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    occasion_code_id = fields.Many2one('occasion.code', string="Occasion code")
    production_id = fields.Many2one('forlife.production', string="Manufacturing Order", domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    type_po = fields.Selection(
        copy=False,
        string="Loại đơn hàng",
        default='',
        selection=[('tax', 'Đơn mua hàng nhập khẩu'),
                   ('cost', 'Đơn mua hàng nội địa'),
                   ])

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
    # approval_logs_ids = fields.One2many('approval.logs', 'purchase_request_id')

    #check button orders_smart_button
    is_check_button_orders_smart_button = fields.Boolean(default=False)

    receiver_id = fields.Many2one('hr.employee', string='Receiver')
    delivery_address = fields.Char('Delivery Address')
    attention = fields.Char('Attention')
    use_department_id = fields.Many2one('hr.department', string='Use Department')

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
        res['department_id'] = self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False
        return res

    @api.onchange('employee_id')
    def onchange_department_id(self):
        if self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    def submit_action(self):
        for record in self:
            record.write({'state': 'confirm'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def cancel(self):
        pass

    def approve_action(self):
        self.write({'state': 'approved'})

    close_request = fields.Boolean('')

    def close_action(self):
        for record in self:
            record.close_request = True
            record.write({'state': 'close'})


    def set_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu yêu cầu mua hàng'),
            'template': '/purchase_request/static/src/xlsx/import_template_pr.xlsx?download=true'
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

    @api.constrains('request_date', 'date_planned')
    def constrains_request_date(self):
        for item in self:
            if item.request_date and item.date_planned:
                time_request = datetime(item.request_date.year, item.request_date.month, item.request_date.day)
                if time_request > item.date_planned:
                    raise ValidationError(_("Expected Arrival must be greater than request date"))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.name.sequence') or 'Pr'
        return super(PurchaseRequest, self).create(vals)

    @api.constrains('order_lines')
    def constrains_order_lines(self):
        if not self.order_lines:
            raise ValidationError(
                _('It is mandatory to enter all the commodity information before confirming the purchase request!'))

    def unlink(self):
        if any(item.state not in ('draft', 'cancel') for item in self):
            raise ValidationError("Bạn chỉ có thể xóa một bản ghi trong trạng thái nháp và hủy")
        return super(PurchaseRequest, self).unlink()

    def create_purchase_orders(self):
        self.is_check_button_orders_smart_button = True
        order_lines_ids = self.filtered(lambda r: r.state != 'close' and r.type_po).order_lines.filtered(lambda r: r.is_close == False).ids
        order_lines_groups = self.env['purchase.request.line'].read_group(domain=[('id', 'in', order_lines_ids)],
                                    fields=['product_id', 'vendor_code', 'product_type'],
                                    groupby=['vendor_code', 'product_type', 'currency_id'], lazy=False)
        purchase_order = self.env['purchase.order']
        occasion_code_id = []
        account_analytic_id = []
        production_id = []
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError('Chỉ tạo được đơn hàng mua với các phiếu yêu cầu mua hàng có trạng thái Phê duyệt! %s') % rec.name
            if rec.occasion_code_id:
                occasion_code_id.append(rec.occasion_code_id.id)
            if rec.account_analytic_id:
                account_analytic_id.append(rec.account_analytic_id.id)
            if rec.production_id:
                production_id.append(rec.production_id.id)
        for group in order_lines_groups:
            keys = {}
            domain = group['__domain']
            vendor_code = group['vendor_code']
            product_type = group['product_type']
            vendor_id = vendor_code[0] if vendor_code else False
            purchase_request_lines = self.env['purchase.request.line'].search(domain)
            po_line_data = []
            for line in purchase_request_lines:
                if line.purchase_quantity == line.order_quantity:
                    continue
                keys.update({
                    line.request_id.name: line.request_id.name
                })
                po_line_data.append((0, 0, {
                    'purchase_request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'purchase_quantity': line.purchase_quantity - line.order_quantity,
                    'exchange_quantity': line.exchange_quantity,
                    'product_qty': (line.purchase_quantity - line.order_quantity) * line.exchange_quantity,
                    'purchase_uom': line.purchase_uom.id,
                    'product_uom': line.purchase_uom.id,
                    'request_purchases': line.purchase_request,
                    'production_id': line.production_id.id,
                    'account_analytic_id': line.account_analytic_id.id,
                    'date_planned': self.date_planned if len(self) == 1 else False,
                }))
            if po_line_data:
                name_pr = []
                for key in keys:
                    name_pr.append(keys[key])
                source_document = ', '.join(name_pr)
                po_data = {
                    'is_inter_company': False,
                    'type_po_cost': rec.type_po,
                    'is_check_readonly_partner_id': True if vendor_id else False,
                    'is_check_readonly_purchase_type': True if product_type else False,
                    'is_purchase_request': True,
                    'partner_id': vendor_id,
                    'purchase_type': product_type,
                    'purchase_request_ids': [(6, 0, purchase_request_lines.mapped('request_id').ids)],
                    'order_line': po_line_data,
                    'occasion_code_ids': occasion_code_id,
                    'account_analytic_ids': account_analytic_id,
                    'source_document': source_document,
                    'production_id': production_id,
                    'date_planned': self.date_planned if len(self) == 1 else False,
                    'currency_id': purchase_request_lines.currency_id.id,
                }
                purchase_order |= purchase_order.create(po_data)
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_order.ids)],
        }

    is_no_more_quantity = fields.Boolean(compute='_compute_true_false_is_check', store=1)
    is_close = fields.Boolean(compute='_compute_true_false_is_check', store=1)
    is_all_line = fields.Boolean(compute='_compute_true_false_is_check', store=1)

    @api.depends('order_lines', 'order_lines.is_no_more_quantity', 'order_lines.is_all_line', 'order_lines.is_close',
                 'order_lines.is_all_line', 'state')
    def _compute_true_false_is_check(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.is_close = all(rec.order_lines.mapped('is_close'))
            rec.is_no_more_quantity = all(rec.order_lines.mapped('is_no_more_quantity'))
            rec.is_all_line = all(rec.order_lines.mapped('is_all_line'))
            if rec.state == 'close':
                if rec.order_lines.mapped('is_all_line'):
                    rec.state = 'approved'
            if rec.close_request:
                rec.state = 'close'

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['state'] = 'draft'
        default['close_request'] = False
        return super().copy(default)

class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line"

    is_close = fields.Boolean(string='Is Close', default=False)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_type = fields.Selection(related='product_id.detailed_type', string='Type', store=1)
    asset_description = fields.Char(string="Asset description")
    description = fields.Char(string="Description", related='product_id.name')
    vendor_code = fields.Many2one('res.partner', string="Vendor")
    currency_id = fields.Many2one('res.currency', 'Currency')

    @api.onchange('vendor_code')
    def onchange_vendor_code(self):
        self.currency_id = self.vendor_code.property_purchase_currency_id.id

    production_id = fields.Many2one('forlife.production', string='Production Order Code', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    request_id = fields.Many2one('purchase.request')
    date_planned = fields.Datetime(string='Expected Arrival')
    request_date = fields.Date(string='Request date')
    purchase_quantity = fields.Integer('Quantity Purchase', digits='Product Unit of Measure', required=True)
    purchase_uom = fields.Many2one('uom.uom', string='UOM Purchase', related='product_id.uom_id', required=True)
    exchange_quantity = fields.Float('Exchange Quantity', required=True, default=1)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Account Analytic Account')
    purchase_order_line_ids = fields.One2many('purchase.order.line', 'purchase_request_line_id')
    purchase_order_id = fields.Many2one('purchase.order')
    order_quantity = fields.Integer('Quantity Order', compute='_compute_order_quantity', store=1)
    is_no_more_quantity = fields.Boolean(compute='_compute_is_no_more_quantity', store=1)
    product_qty = fields.Float(string='Quantity', digits=(16, 0), compute='_compute_product_qty', store=1)
    purchase_request = fields.Char(related='request_id.name')
    state = fields.Selection(
        string="Status",
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('close', 'Close'),
                   ])


    @api.depends('purchase_quantity', 'exchange_quantity')
    def _compute_product_qty(self):
        for line in self:
            if line.purchase_quantity and line.exchange_quantity:
                line.product_qty = line.purchase_quantity * line.exchange_quantity
            else:
                line.product_qty = line.purchase_quantity

    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.product_qty', 'purchase_order_line_ids.order_id.custom_state')
    def _compute_order_quantity(self):
        for rec in self:
            if rec.purchase_order_line_ids.order_id.filtered(lambda r: r.custom_state == 'approved'):
                rec.order_quantity = sum(rec.purchase_order_line_ids.mapped('product_qty'))
                ### sửa thành vào hàm approved ở po

    @api.depends('purchase_quantity', 'order_quantity')
    def _compute_is_no_more_quantity(self):
        for rec in self:
            rec.is_no_more_quantity = rec.purchase_quantity <= rec.order_quantity

    @api.constrains('purchase_quantity', 'exchange_quantity')
    def constrains_purchase_quantity(self):
        for item in self:
            if item.purchase_quantity <= 0:
                raise ValidationError("Quantity purchase must be greater than 0!")
            if item.exchange_quantity <= 0:
                raise ValidationError('Exchange quantity must be greater than 0!')

    is_all_line = fields.Boolean('', compute='_compute_is_all_line', store=1)

    @api.depends('is_close', 'is_no_more_quantity')
    def _compute_is_all_line(self):
        for rec in self:
            if not rec.is_close and not rec.is_no_more_quantity:
                rec.is_all_line = False
            if not rec.is_close and rec.is_no_more_quantity:
                rec.is_all_line = True
            if rec.is_close and not rec.is_no_more_quantity:
                rec.is_all_line = True
            if rec.is_close and rec.is_no_more_quantity:
                rec.is_all_line = True

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
