from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import json
from io import BytesIO
import xlsxwriter
import base64


class StockTransferRequest(models.Model):
    _name = 'stock.transfer.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Stock Transfer'
    _check_company_auto = True

    name = fields.code = fields.Char(string="Name", default="New", copy=False)
    request_date = fields.Datetime(string="Request Date", default=lambda self: fields.datetime.now(), required=True)
    date_planned = fields.Datetime(string='Expected Arrival', required=True)
    request_employee_id = fields.Many2one('hr.employee', string="Employee")
    user_id = fields.Many2one('res.users', string="Người yêu cầu", required=True)
    department_id = fields.Many2one('hr.department', string="Department", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_confirm', 'Wait Confirm'),
                   ('approved', 'Approved'),
                   ('done', 'Done'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft', copy=False)
    request_lines = fields.One2many('transfer.request.line', 'request_id', string='Chi tiết', copy=True)
    stock_transfer_ids = fields.One2many('stock.transfer', 'stock_request_id', string="Stock Transfer", copy=False)
    rejection_reason = fields.Text()
    created_stock_transfer = fields.Boolean(default=False)
    count_stock_transfer = fields.Integer(compute="compute_count_stock_transfer", copy=False)
    is_no_more_quantity = fields.Boolean(compute='compute_is_no_more_quantity', store=1)
    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], copy=False)
    location_id = fields.Many2one('stock.location', "Từ kho", check_company=True)
    location_dest_id = fields.Many2one('stock.location', "Đến kho", check_company=True)
    note = fields.Text(string='Ghi chú')
    purchase_id = fields.Many2one('purchase.order', string='Đơn mua hàng', domain=[('is_return', '=', False)])
    total_request_qty = fields.Float(string='Tổng số lượng yc', compute='_compute_total_qty', store=True)
    total_in_qty = fields.Float(string='Tổng số lượng thực xuất', compute='_compute_total_qty', store=True)
    total_out_qty = fields.Float(string='Tổng số lượng thực nhận', compute='_compute_total_qty', store=True)

    @api.depends('request_lines.plan_quantity', 'request_lines.quantity_reality_receive', 'request_lines.quantity_reality_transfer')
    def _compute_total_qty(self):
        for rec in self:
            total_request_qty = 0
            total_in_qty = 0
            total_out_qty = 0
            for line in rec.request_lines:
                total_request_qty += line.plan_quantity
                total_in_qty += line.quantity_reality_receive
                total_out_qty += line.quantity_reality_transfer
            rec.total_request_qty = total_request_qty
            rec.total_in_qty = total_in_qty
            rec.total_out_qty = total_out_qty

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['request_employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['user_id'] = self.env.user.id if self.env.user else False
        res['department_id'] = self.env.user.department_default_id.id if self.env.user.department_default_id else False
        res['request_date'] = datetime.now()
        if "import_file" in self.env.context:
            if not self.env.user:
                raise ValidationError(_("Tài khoản chưa thiết lập nhân viên"))
            if not self.env.user.department_default_id:
                raise ValidationError(_("Tài khoản chưa thiết lập phòng ban"))
        return res

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if not self.user_id.department_default_id:
            raise ValidationError("Vui lòng báo quản trị viên cấu hình phòng ban mặc định cho Người dùng %s!" % self.user_id.name)
        self.department_id = self.user_id.department_default_id.id

    @api.constrains('request_date', 'date_planned')
    def constrains_request_planed_dated(self):
        for item in self:
            if item.request_date > item.date_planned:
                raise ValidationError('Hạn xử lý phải lớn hơn ngày tạo')

    @api.onchange('production_id')
    def _onchange_production_id(self):
        if self.request_lines:
            self.request_lines = False

        request_lines = []
        if self.production_id.material_import_ids:
            for production_material_id in self.production_id.material_import_ids:
                request_lines.append((0, 0, {
                    'product_id': production_material_id.product_id.id,
                    'plan_quantity': production_material_id.total,
                    'uom_id': production_material_id.uom_id.id or production_material_id.product_id.uom_id.id,
                    'production_to': self.production_id.id,
                    'location_id': self.location_id.id or False,
                    'location_dest_id': self.location_dest_id.id or False,
                }))
            self.write({
                'request_lines': request_lines
            })

    @api.onchange('location_id')
    def onchange_location_id(self):
        for r in self:
            r.request_lines.write({
                'location_id': r.location_id.id or False
            })

    @api.onchange('location_dest_id')
    def onchange_location_dest_id(self):
        for r in self:
            r.request_lines.write({
                'location_dest_id': r.location_dest_id.id or False
            })

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu yêu cầu điều chuyển'),
            'template': '/forlife_stock/static/src/xlsx/template_import_ycdc.xlsx?download=true'
        }]

    def action_wait_confirm(self):
        self.write({
            'state': 'wait_confirm',
        })

    def action_draft(self):
        self.write({
            'state': 'draft'
        })

    def action_done(self):
        self.write({
            'state': 'done'
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel',
        })

    def action_approve(self):
        for record in self:
            value = {}
            for item in record.request_lines.filtered(lambda x: x.quantity_remaining > 0):
                key = str(item.location_id.id) + '_and_' + str(item.location_dest_id.id)
                data_stock_transfer_line = (0, 0, {
                    'product_id': item.product_id.id,
                    'uom_id': item.uom_id.id,
                    'qty_plan': item.quantity_remaining,
                    'work_from': item.production_from.id,
                    'work_to': item.production_to.id,
                    'product_str_id': item.id,
                    'qty_out': 0,
                    'qty_in': 0,
                    'is_from_button': True,
                    'qty_plan_tsq': item.quantity_remaining,
                    'stock_request_id': record.id
                })
                dic_data = {
                    'state': 'approved',
                    'employee_id': record.user_id.employee_id.id or False,
                    'department_id': record.department_id.id,
                    'stock_request_id': record.id,
                    'location_id': item.location_id.id,
                    'location_name': item.location_id.location_id.name+'/'+item.location_id.name,
                    'location_dest_id': item.location_dest_id.id,
                    'location_dest_name': item.location_dest_id.location_id.name+'/'+item.location_dest_id.name,
                    'work_to': record.production_id.id or False,
                    'stock_transfer_line': [data_stock_transfer_line]
                }
                if value.get(key):
                    value[key]['stock_transfer_line'].append(data_stock_transfer_line)
                else:
                    value.update({
                        key: dic_data
                    })
            for item in value:
                stock_transfer_id = self.env['stock.transfer'].create(value.get(item))
            record.write({
                'created_stock_transfer': True,
                'state': 'approved'
            })
            return {
                'name': _('List Stock Transfer'),
                'view_mode': 'tree,form',
                'res_model': 'stock.transfer',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('stock_request_id', '=', record.id)],
                'context': {
                    'stock_request_id': self.id,
                    'create': True,
                    'delete': True,
                    'edit': True
                }
            }

    @api.constrains('request_lines')
    def constrains_request_lines(self):
        if not self.request_lines and self.state != 'draft' and self.state:
            raise ValidationError(
                _('It is mandatory to enter all the commodity information before confirming the stock transfer request!'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.transfer.request.name.sequence') or 'STR'
        res = super(StockTransferRequest, self).create(vals_list)
        # res.write({'state': 'draft'})
        return res

    def write(self, values):
        res = super(StockTransferRequest, self).write(values)
        for r in self:
            if not r.request_lines:
                raise ValidationError("Vui lòng nhập ít nhất 1 dòng chi tiết Sản phẩm!")
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("You only delete a record in draft and cancel status")
        return super(StockTransferRequest, self).unlink()

    def action_stock_transfer(self):
        return {
            'name': _('List Stock Transfer'),
            'view_mode': 'tree,form',
            'res_model': 'stock.transfer',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('stock_request_id', '=', self.id)],
            'context': {
                'stock_request_id': self.id,
                'create': True,
                'delete': True,
                'edit': True
            }
        }

    def compute_count_stock_transfer(self):
        for item in self:
            item.count_stock_transfer = len(item.stock_transfer_ids)

    @api.depends('request_lines', 'request_lines.quantity_remaining', 'stock_transfer_ids', 'stock_transfer_ids.state')
    def compute_is_no_more_quantity(self):
        for item in self:
            all_equal_remaining = all(x == 0 for x in item.request_lines.mapped('quantity_remaining'))
            all_equal_parent_done = all(x == 'done' for x in item.stock_transfer_ids.mapped('state'))
            if all_equal_remaining and all_equal_parent_done:
                item.is_no_more_quantity = True
            else:
                item.is_no_more_quantity = False


class TransferRequestLine(models.Model):
    _name = 'transfer.request.line'
    _description = 'Transfer Request Line'

    product_id = fields.Many2one('product.product', string="Product", required=True, copy=True)
    uom_id = fields.Many2one('uom.uom', string='Đơn vị', required=True)
    location_id = fields.Many2one('stock.location', string="Whs From", required=True)
    location_dest_id = fields.Many2one('stock.location', string="Whs To", required=True)
    request_id = fields.Many2one('stock.transfer.request', string="Stock Transfer Request", required=True, ondelete='cascade')
    quantity = fields.Float(default=1, string='Quantity', required=True)
    plan_quantity = fields.Float(string="Plan Quantity")
    quantity_reality_transfer = fields.Float(string="Quantity reality transfer", compute='compute_quantity_reality_transfer', )
    quantity_reality_receive = fields.Float(string="Quantity reality receive", compute='compute_quantity_reality_receive', )
    quantity_remaining = fields.Float(string="Quantity remaining", compute='compute_quantity_remaining')
    stock_transfer_line_ids = fields.One2many('stock.transfer.line', 'product_str_id')
    production_from = fields.Many2one('forlife.production', string="Từ LSX", domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    production_to = fields.Many2one('forlife.production', string="Đến LSX", domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')

    @api.depends('stock_transfer_line_ids', 'stock_transfer_line_ids.qty_out')
    def compute_quantity_reality_transfer(self):
        for item in self:
            data_str_line = item.get_value_str_line()
            if data_str_line:
                item.quantity_reality_transfer = sum(data_str_line.mapped('qty_out'))
            else:
                item.quantity_reality_transfer = 0

    @api.depends('stock_transfer_line_ids', 'stock_transfer_line_ids.qty_in')
    def compute_quantity_reality_receive(self):
        for item in self:
            data_str_line = item.get_value_str_line()
            if data_str_line:
                item.quantity_reality_receive = sum(data_str_line.mapped('qty_in'))
            else:
                item.quantity_reality_receive = 0

    def get_value_str_line(self):
        return self.env['stock.transfer.line'].search([('is_parent_done', '=', True), ('product_str_id', '=', self.id)])

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id

    @api.depends('plan_quantity', 'quantity_reality_receive')
    def compute_quantity_remaining(self):
        for item in self:
            item.quantity_remaining = item.plan_quantity - item.quantity_reality_receive

    @api.constrains('plan_quantity')
    def constrains_plan_quantity(self):
        for rec in self:
            if rec.plan_quantity <= 0:
                raise ValidationError(_("Plan quantity should not be less than or equal to 0 !!"))

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('import_file'):
            for vals in vals_list:
                product = self.env['product.product'].browse(vals.get('product_id'))
                if product and vals.get('uom_id') and vals.get('uom_id') != product.uom_id.id:
                    raise ValidationError(_("Đơn vị nhập vào không khớp với đơn vị lưu kho của sản phẩm [%s] %s" % (product.code, product.name)))
        return super(TransferRequestLine, self).create(vals_list)


class Location(models.Model):
    _inherit = "stock.location"
    _rec_names_search = ['code', 'complete_name', 'barcode']


class AssetsAssets(models.Model):
    _inherit = 'assets.assets'
    _rec_names_search = ['code', 'name']
