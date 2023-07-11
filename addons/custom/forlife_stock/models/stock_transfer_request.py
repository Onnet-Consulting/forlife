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

    name = fields.code = fields.Char(string="Name", default="New", copy=False)
    request_date = fields.Datetime(string="Request Date", default=lambda self: fields.datetime.now(), required=True)
    date_planned = fields.Datetime(string='Expected Arrival', required=True)
    request_employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    department_id = fields.Many2one('hr.department', string="Department", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_confirm', 'Wait Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('done', 'Done')], default='draft', copy=False)
    request_lines = fields.One2many('transfer.request.line', 'request_id', string='Yêu cầu', copy=True)
    stock_transfer_ids = fields.One2many('stock.transfer', 'stock_request_id', string="Stock Transfer", copy=False)
    rejection_reason = fields.Text()
    # approval_logs_ids = fields.One2many('approval.logs.stock', 'stock_transfer_request_id')
    created_stock_transfer = fields.Boolean(default=False)
    count_stock_transfer = fields.Integer(compute="compute_count_stock_transfer", copy=False)
    is_no_more_quantity = fields.Boolean(compute='compute_is_no_more_quantity', store=1)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['request_employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['department_id'] = self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False
        res['request_date'] = datetime.now()
        if "import_file" in self.env.context:
            if not self.env.user.employee_id:
                raise ValidationError(_("Tài khoản chưa thiết lập nhân viên"))
            if not self.env.user.employee_id.department_id:
                raise ValidationError(_("Tài khoản chưa thiết lập phòng ban"))
        return res

    @api.onchange('request_employee_id')
    def _onchange_request_employee_id(self):
        self.department_id = self.request_employee_id.department_id.id

    @api.constrains('request_date', 'date_planned')
    def constrains_request_planed_dated(self):
        for item in self:
            if item.request_date > item.date_planned:
                raise ValidationError('Hạn xử lý phải lớn hơn ngày tạo')

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu yêu cầu điều chuyển'),
            'template': '/forlife_stock/static/src/xlsx/template_ycdc.xlsx?download=true'
        }]

    def action_wait_confirm(self):
        for record in self:
            record.write({'state': 'wait_confirm',
                          # 'approval_logs_ids': [(0, 0, {
                          #     'request_approved_date': date.today(),
                          #     'approval_user_id': record.env.user.id,
                          #     'note': 'Wait Confirm',
                          #     'state_request': 'wait_confirm',
                          # })],
                          })

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_approve(self):
        for record in self:
            value = {}
            for item in record.request_lines:
                if item.quantity_remaining > 0:
                    key = str(item.location_id.id) + '_and_' + str(item.location_dest_id.id)
                    data_stock_transfer_line = (
                        0, 0, {'product_id': item.product_id.id, 'uom_id': item.uom_id.id,
                               'qty_plan': item.quantity_remaining,
                               'work_from': item.production_from,
                               'work_to': item.production_to,
                               'product_str_id': item.id, 'qty_out': 0, 'qty_in': 0, 'is_from_button': True,
                               'qty_plan_tsq': item.quantity_remaining, 'stock_request_id': record.id})
                    dic_data = {'state': 'draft',
                                'employee_id': record.request_employee_id.id,
                                'stock_request_id': record.id, 'location_id': item.location_id.id,
                                'location_dest_id': item.location_dest_id.id,
                                'stock_transfer_line': [data_stock_transfer_line]
                                }
                    if value.get(key):
                        value[key]['stock_transfer_line'].append(data_stock_transfer_line)
                    else:
                        value.update({
                            key: dic_data
                        })
            for item in value:
                data_stock_transfer = self.env['stock.transfer'].create(value.get(item))
            record.write({'created_stock_transfer': True, 'state': 'approved'})
            context = {'stock_request_id': self.id, 'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('List Stock Transfer'),
                'view_mode': 'tree,form',
                'res_model': 'stock.transfer',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('stock_request_id', '=', record.id)],
                'context': context
            }

    def action_done(self):
        for record in self:
            record.write({'state': 'done',
                          # 'approval_logs_ids': [(0, 0, {
                          #     'request_approved_date': date.today(),
                          #     'approval_user_id': record.env.user.id,
                          #     'note': 'Done',
                          #     'state_request': 'done',
                          # })],
                          })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel',
                          # 'approval_logs_ids': [(0, 0, {
                          #     'request_approved_date': date.today(),
                          #     'approval_user_id': record.env.user.id,
                          #     'note': 'Cancel',
                          #     'state_request': 'cancel',
                          # })],
                          })

    # @api.onchange('request_lines')
    # def onchange_request_lines(self):
    #     for record in self.request_lines:
    #         if record.location_id and record.location_dest_id:
    #             if record.location_id.id == record.location_dest_id.id:
    #                 raise ValidationError(_("Source Warehouse And Destination Warehouse must not overlap"))

    @api.constrains('request_lines')
    def constrains_request_lines(self):
        if not self.request_lines:
            raise ValidationError(
                _('It is mandatory to enter all the commodity information before confirming the stock transfer request!'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.transfer.request.name.sequence') or 'STR'
        return super(StockTransferRequest, self).create(vals)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("You only delete a record in draft and cancel status")
        return super(StockTransferRequest, self).unlink()

    @api.onchange('request_employee_id')
    def onchange_department_id(self):
        if self.request_employee_id.department_id:
            self.department_id = self.request_employee_id.department_id

    def create_stock_transfer(self):
        if len(self.ids) > 1:
            raise ValidationError(_('You can only select 1 record'))
        else:
            for record in self:
                if record.state == 'approved':
                    value = {}
                    for item in record.request_lines:
                        if item.quantity_remaining > 0:
                            key = str(item.location_id.id) + '_and_' + str(item.location_dest_id.id)
                            data_stock_transfer_line = (
                                0, 0, {'product_id': item.product_id.id, 'uom_id': item.uom_id.id,
                                       'qty_plan': item.plan_quantity, 'product_str_id': item.id, 'qty_out': 0,
                                       'qty_in': 0,
                                       'is_from_button': True, 'qty_plan_tsq': item.quantity_remaining})
                            dic_data = {'state': 'draft',
                                        'stock_request_id': record.id, 'location_id': item.location_id.id,
                                        'location_dest_id': item.location_dest_id.id,
                                        'stock_transfer_line': [data_stock_transfer_line]
                                        }
                            if value.get(key):
                                value[key]['stock_transfer_line'].append(data_stock_transfer_line)
                            else:
                                value.update({
                                    key: dic_data
                                })
                    for item in value:
                        data_stock_transfer = self.env['stock.transfer'].create(value.get(item))
                    record.write({'created_stock_transfer': True})
                    context = {'stock_request_id': self.id, 'create': True, 'delete': True, 'edit': True}
                    return {
                        'name': _('List Stock Transfer'),
                        'view_mode': 'tree,form',
                        'res_model': 'stock.transfer',
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'domain': [('stock_request_id', '=', record.id)],
                        'context': context
                    }
                else:
                    raise ValidationError(_('The record is not in approved state'))

    def action_stock_transfer(self):
        context = {'stock_request_id': self.id, 'create': True, 'delete': True, 'edit': True}
        return {
            'name': _('List Stock Transfer'),
            'view_mode': 'tree,form',
            'res_model': 'stock.transfer',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('stock_request_id', '=', self.id)],
            'context': context
        }

    def compute_count_stock_transfer(self):
        for item in self:
            item.count_stock_transfer = len(item.stock_transfer_ids)

    @api.depends('request_lines', 'request_lines.quantity_remaining',
                 'stock_transfer_ids', 'stock_transfer_ids.state')
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
    request_id = fields.Many2one('stock.transfer.request', string="Stock Transfer Request", required=True,
                                 ondelete='cascade')
    quantity = fields.Float(default=1, string='Quantity', required=True)
    plan_quantity = fields.Integer(string="Plan Quantity")
    quantity_reality_transfer = fields.Integer(string="Quantity reality transfer",
                                               compute='compute_quantity_reality_transfer', )
    quantity_reality_receive = fields.Integer(string="Quantity reality receive",
                                              compute='compute_quantity_reality_receive', )
    quantity_remaining = fields.Integer(string="Quantity remaining", compute='compute_quantity_remaining')
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

    @api.model
    def create(self, vals):
        if self.env.context.get('import_file'):
            product = self.env['product.product'].browse(vals.get('product_id'))
            if vals.get('uom_id') and vals.get('uom_id') != product.uom_id.id:
                raise ValidationError(_("Đơn vị khác đơn vị của sản phẩm"))
        return super(TransferRequestLine, self).create(vals)


class Location(models.Model):
    _inherit = "stock.location"
    _rec_names_search = ['code', 'complete_name', 'barcode']