from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import base64
import xlsxwriter
from io import BytesIO
import pytz
from pytz import UTC


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Request"

    name = fields.Char(string="Request name", required=True, default='New', copy=False)
    user_id = fields.Many2one('res.users', string="Người yêu cầu", required=True)
    employee_id = fields.Many2one('hr.employee', string='User Request')
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    date_planned = fields.Datetime(string='Expected Arrival', required=True)
    request_date = fields.Date(string='Request date', default=lambda self: fields.Date.context_today(self), required=True)
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

    @api.onchange('date_planned')
    def _onchange_line_date_planned(self):
        for rec in self.order_lines:
            rec.date_planned = self.date_planned

    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            if 'request_date' not in fields:
                raise ValidationError(_("File nhập phải chứa ngày yêu cầu"))
            for record in data:
                if 'order_lines/product_id' in fields and not record[fields.index('order_lines/product_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường sản phẩm"))
                if 'order_lines/purchase_quantity' in fields and not record[fields.index('order_lines/purchase_quantity')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng đặt mua"))
                if 'order_lines/exchange_quantity' in fields and not record[fields.index('order_lines/exchange_quantity')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng quy đổi"))
                if 'order_lines/purchase_uom' in fields and not record[fields.index('order_lines/purchase_uom')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường đơn vị mua"))
                if 'order_lines/request_date' in fields and not record[fields.index('order_lines/request_date')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường ngày yêu cầu"))
                if 'order_lines/date_planned' in fields and not record[fields.index('order_lines/date_planned')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường ngày nhận hàng dự kiến"))
        return super().load(fields, data)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['user_id'] = self.env.user.id if self.env.user else False
        res['department_id'] = self.env.user.department_default_id.id if self.env.user.department_default_id else False
        if "import_file" in self.env.context:
            if not self.env.user:
                raise ValidationError(_("Tài khoản chưa thiết lập nhân viên"))
            if not self.env.user.department_default_id:
                raise ValidationError(_("Tài khoản chưa thiết lập phòng ban"))
        return res

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id.department_default_id:
            self.department_id = self.user_id.department_default_id.id

    def submit_action(self):
        for record in self:
            for line in record.order_lines:
                if not line.purchase_uom:
                    raise UserError(_('Đơn vị mua của sản phẩm %s chưa được chọn') % line.product_id.name)
                if not line.date_planned:
                    raise UserError(_('Ngày nhận hàng dự kiến của sản phẩm %s chưa được chọn') % line.product_id.name)
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
            'template': '/purchase_request/static/src/xlsx/template_import_pr.xlsx?download=true'
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

    def convert_to_local(self, datetime=datetime.today(), tz=False):
        if not tz:
            tz = self._context.get('tz') or self.env.user.tz or 'UTC'
        local_time = pytz.utc.localize(datetime).astimezone(pytz.timezone(tz))
        return local_time.replace(tzinfo=None)

    @api.constrains('request_date', 'date_planned')
    def constrains_request_date(self):
        for item in self:
            if item.request_date and item.date_planned:
                time_plan = self.convert_to_local(item.date_planned)
                time_request = datetime(item.request_date.year, item.request_date.month, item.request_date.day)
                if time_request > time_plan:
                    raise ValidationError(_("Expected Arrival must be greater than request date"))

    @api.model_create_multi
    def create(self, vals):
        if not isinstance(vals, list):
            vals = [vals]
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('purchase.request.name.sequence') or 'Pr'
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
        order_lines_ids = self.filtered(lambda r: r.state != 'close' and r.type_po).order_lines.filtered(lambda r: r.is_close == False)
        groups = {}
        for line in order_lines_ids:
            key = str(line.vendor_code.id) + '-' + str(line.purchase_product_type)
            if groups.get(key, False):
                groups[key].append(line)
            else:
                groups[key] = [line]
        purchase_order = self.env['purchase.order']
        # occasion_code_id = []
        account_analytic_id = []
        production_id = []
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_('Chỉ tạo được đơn hàng mua với các phiếu yêu cầu mua hàng có trạng thái Phê duyệt! %s') % rec.name)
            # if rec.occasion_code_id:
            #     occasion_code_id.append(rec.occasion_code_id.id)
            # if rec.account_analytic_id:
            #     account_analytic_id.append(rec.account_analytic_id.id)
            if rec.production_id:
                production_id.append(rec.production_id.id)
        for group in groups:
            lines = groups[group]
            keys = {}
            vendor_code = lines[0].vendor_code
            product_type = lines[0].purchase_product_type
            vendor_id = vendor_code.id if vendor_code else False
            po_line_data = []
            for line in lines:
                if line.purchase_quantity == line.order_quantity:
                    continue
                keys.update({
                    line.request_id.name: line.request_id.name
                })
                po_line_data.append((0, 0, {
                    'purchase_request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'asset_code': line.asset_code.id,
                    'name': line.product_id.name,
                    'purchase_quantity': line.purchase_quantity - line.order_quantity,
                    'exchange_quantity': line.exchange_quantity,
                    'product_qty': (line.purchase_quantity - line.order_quantity) * line.exchange_quantity,
                    'purchase_uom': line.purchase_uom.id or line.product_id.uom_po_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'receive_date': line.date_planned,
                    'request_purchases': line.purchase_request,
                    'production_id': line.production_id.id,
                    'account_analytic_id': line.account_analytic_id.id,
                    'date_planned': line.date_planned,
                }))
            if po_line_data:
                name_pr = []
                for key in keys:
                    name_pr.append(keys[key])
                source_document = ', '.join(name_pr)
                po_data = {
                    'is_inter_company': False,
                    'type_po_cost': self.type_po,
                    'is_check_readonly_partner_id': True if vendor_id else False,
                    'is_check_readonly_purchase_type': True if product_type else False,
                    'is_purchase_request': True,
                    'partner_id': vendor_id,
                    'purchase_type': product_type,
                    'purchase_request_ids': [(6, 0, lines[0].request_id.ids)],
                    'order_line': po_line_data,
                    'occasion_code_id': self.occasion_code_id.id if self.occasion_code_id else False,
                    'account_analytic_id': self.account_analytic_id.id if self.account_analytic_id else False,
                    'source_document': source_document,
                    'date_planned': self.date_planned if len(self) == 1 else False,
                    'currency_id': lines[0].currency_id.id if lines[0].currency_id else self.env.company.currency_id.id,
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
    purchase_product_type = fields.Selection(related='product_id.product_type', string='Type', store=0)
    asset_description = fields.Char(string="Asset description")
    asset_code = fields.Many2one('assets.assets', string='Tài sản')
    description = fields.Char(string="Mô tả")
    vendor_code = fields.Many2one('res.partner', string="Vendor")
    currency_id = fields.Many2one('res.currency', 'Currency')
    production_id = fields.Many2one('forlife.production', string='Production Order Code', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    request_id = fields.Many2one('purchase.request')
    date_planned = fields.Datetime(string='Expected Arrival', required=True)
    request_date = fields.Date(string='Request date', required=True)
    purchase_quantity = fields.Integer('Quantity Purchase', digits='Product Unit of Measure', required=True)
    purchase_uom = fields.Many2one('uom.uom', string='UOM Purchase', required=True)
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

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.write({
            'description': self.product_id.name,
            'purchase_uom': self.product_id.uom_id.id,
        })

    @api.onchange('product_id')
    def onchange_product_id_comput_assets(self):
        if self.product_id.product_type == 'asset':
            account = self.product_id.categ_id.property_account_expense_categ_id
            if account:
                return {'domain': {'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                  ('company_id', '=', self.request_id.company_id.id),
                                                  ('asset_account', '=', account.id)]}}
            return {'domain': {'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                              ('company_id', '=', self.request_id.company_id.id)]}}

    @api.onchange('vendor_code')
    def onchange_vendor_code(self):
        self.currency_id = self.vendor_code.property_purchase_currency_id.id

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
                raise ValidationError(_("Quantity purchase must be greater than 0!"))
            if item.exchange_quantity <= 0:
                raise ValidationError(_('Exchange quantity must be greater than 0!'))

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

class OccasionCode(models.Model):
    _inherit = 'occasion.code'
    _rec_names_search = ['code', 'name']
