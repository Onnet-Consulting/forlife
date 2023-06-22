# import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime


class StockTransfer(models.Model):
    _name = 'stock.transfer'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Stock Transfer'
    _order = "write_date desc"

    name = fields.code = fields.Char(string="Reference", default="New", copy=False)
    location_id = fields.Many2one('stock.location', string="Whs From", required=1)
    location_dest_id = fields.Many2one('stock.location', string="Whs To", required=1)
    work_from = fields.Many2one('forlife.production', string="LSX From", domain=[('state', '=', 'approved'), ('status', '=', 'in_approved')])
    work_to = fields.Many2one('forlife.production', string="LSX To", domain=[('state', '=', 'approved'), ('status', '=', 'in_approved')])
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")
    employee_id = fields.Many2one('hr.employee', string="User", default=lambda self: self.env.user.employee_id.id, required=1)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string="Phòng ban", related='employee_id.department_id')
    reference_document_id = fields.Many2one('stock.transfer.request', string="Transfer Request")
    production_order_id = fields.Many2one('production.order', string="Production Order")
    create_date = fields.Datetime(string='Create Date', default=lambda self: fields.datetime.now())
    document_type = fields.Selection(
        string="Type",
        selection=[('same_branch', 'Same Branch'),
                   ('difference_branch', 'Difference Branch'),
                   ('excess_arising_lack_arise', 'Excess Arising/Lack Arise')], default='same_branch', required=1, compute='_compute_document_type')
    type = fields.Selection([
        ('excess', 'Điều chuyển phát sinh thừa'),
        ('lack', 'Điều chuyển phát sinh thiếu'),
    ], string='Type')
    method_transfer = fields.Selection(
        string="Method",
        selection=[('transfer_between_warehouse', 'Transfer Between Warehouse'),
                   ('transfer_between_production_order', 'Transfer Between Production Order')], default='transfer_between_warehouse', required=1)
    state = fields.Selection(
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_approve', 'Wait Approve'),
                   ('approved', 'Approved'),
                   ('out_approve', 'Out Approve'),
                   ('in_approve', 'In Approve'),
                   ('done', 'Done'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft')
    is_diff_transfer = fields.Boolean(string="Diff Transfer", default=False)
    stock_transfer_line = fields.One2many('stock.transfer.line', 'stock_transfer_id', copy=True, string='Line')
    total_package = fields.Float(string='Total Package (Number)')
    total_weight = fields.Float(string='Total Weight (Kg)')
    reference_document = fields.Char()
    # approval_logs_ids = fields.One2many('approval.logs.stock', 'stock_transfer_id')
    note = fields.Text("Ghi chú")
    date_transfer = fields.Datetime("Ngày xác nhận xuất", default=datetime.now())
    date_in_approve = fields.Datetime("Ngày xác nhận nhập", default=datetime.now())

    @api.onchange('work_from')
    def _onchange_work_from(self):
        self.stock_transfer_line.write({
            'work_from': self.work_from.id,
        })

    @api.onchange('work_to')
    def _onchange_work_to(self):
        self.stock_transfer_line.write({
            'work_to': self.work_to.id,
        })

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_wait_approve(self):
        for record in self:
            record.write({'state': 'wait_approve'})

    def action_out_approve(self):
        self.ensure_one()  # vì cần bật popup khi người dùng chọn không đủ số lượng
        if any(line.qty_out == 0 for line in self.stock_transfer_line):
            view = self.env.ref('forlife_stock.stock_transfer_popup_out_confirm_view_form')
            return {
                'name': 'Điều chuyển ngay?',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.transfer.popup.confirm',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': dict(self.env.context, default_stock_transfer_id=self.id),
            }
        return self._action_out_approve()

    def _action_out_approve(self):
        self.ensure_one()
        self._validate_product_quantity()
        self._validate_product_tolerance('out')
        stock_transfer_line_less = self.stock_transfer_line.filtered(lambda r: r.qty_out < r.qty_plan)
        if stock_transfer_line_less:
            self._out_approve_less_quantity(stock_transfer_line_less)
        self._update_forlife_production()
        self.write({'state': 'out_approve'})
        if stock_transfer_line_less:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'Có phiếu dở dang đã được tạo cần xác nhận!',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def _update_forlife_production(self):
        for line in self.stock_transfer_line:
            if line.work_from:
                forlife_production_service_cost = line.work_from.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
                if not forlife_production_service_cost:
                    continue
                forlife_production_service_cost.write({
                    'forlife_production_stock_transfer_line_ids': [(4, line.id)],
                })

    def _validate_product_tolerance(self, type='out'):
        self.ensure_one()
        for line in self.stock_transfer_line:
            line.validate_product_tolerance(type)

    def _validate_product_quantity(self):
        self.ensure_one()
        location = self.location_id
        for line in self.stock_transfer_line:
            line.validate_product_quantity(location)

    def _out_approve_with_confirm(self):
        self.ensure_one()
        for line in self.stock_transfer_line.filtered(lambda r: r.qty_out == 0):
            line.write({
                'qty_out': line.qty_plan
            })
        self._action_out_approve()

    def _create_move_import_int(self, pickking, location_id, location_dest_id):
        warehouse_type_id_ec = self.env['stock.warehouse.type'].sudo().search([('code', '=', 5)])
        warehouse_type_master = self.env.ref('forlife_base.stock_warehouse_type_01', raise_if_not_found=False).id
        s_location_pos = self.env.ref('forlife_stock.warehouse_for_pos', raise_if_not_found=False).id
        s_location_sell_ecommerce = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        warehouse_id = location_id.warehouse_id.whs_type.id
        warehouse_dest_id = location_dest_id.warehouse_id.whs_type.id
        if location_dest_id.stock_location_type_id.id in [s_location_pos] and warehouse_id in [warehouse_type_master] and location_dest_id.id_deposit and location_dest_id.account_stock_give:
            return self._create_move_given(pickking, location_dest_id, type_create='in')
        elif location_id.stock_location_type_id.id in [s_location_pos] and warehouse_dest_id in [warehouse_type_master] and location_id.id_deposit and location_id.account_stock_give:
            return self._create_move_given(pickking, location_id, type_create='out')
        elif location_id.stock_location_type_id.id in [s_location_sell_ecommerce, s_location_pos] and location_dest_id.stock_location_type_id.id in [s_location_sell_ecommerce, s_location_pos]:
            loc = location_id if location_id.id_deposit and location_id.account_stock_give else False
            loc_dest = location_dest_id if location_dest_id.id_deposit and location_dest_id.account_stock_give else False
            if not loc and not loc_dest:
                return False
            elif not loc and loc_dest:
                return self._create_move_given(pickking, loc_dest, type_create='out')
            elif loc and not loc_dest:
                return self._create_move_given(pickking, loc, type_create='out')
            return self._create_move_given(pickking, location_id, type_create='out')

        return True

    def _create_move_given(self, picking, location, type_create):
        for d in picking.move_ids_without_package:
            if type_create == 'out':
                account_id_debit = d.product_id.categ_id.property_stock_valuation_account_id.id
                account_id_credit = location.account_stock_give.id
            else:
                account_id_debit = location.account_stock_give.id
                account_id_credit = d.product_id.categ_id.property_stock_valuation_account_id.id
            accounts_data = d.product_id.product_tmpl_id.get_product_accounts()
            if not accounts_data['stock_journal']:
                raise ValidationError(_('Chưa cấu hình sổ nhật kí kho của danh mục sản phẩm này!'))
            move_vals = {
                'journal_id': accounts_data['stock_journal'].id,
                'date': datetime.now(),
                'ref': picking.name,
                'move_type': 'entry',
                'stock_move_id': d.id,
                'line_ids': [
                    (0, 0, {
                        'name': picking.name,
                        'account_id': account_id_debit,
                        'debit': d.quantity_done * d.product_id.standard_price,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': picking.name,
                        'account_id': account_id_credit,
                        'debit': 0.0,
                        'credit': d.quantity_done*d.product_id.standard_price,
                    })
                ]
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
        return True

    def _out_approve_less_quantity(self, stock_transfer_line_less):
        self.ensure_one()
        for line in stock_transfer_line_less:
            self.env['stock.transfer'].create({
                'reference_document': self.name,
                'employee_id': self.employee_id.id,
                'document_type': 'excess_arising_lack_arise',
                'stock_request_id': self.stock_request_id.id,
                'type': 'lack',
                'is_diff_transfer': True,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'work_from': self.work_from.id,
                'work_to': self.work_to.id,
                'state': 'approved',
                'stock_transfer_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': line.qty_plan - line.qty_out,
                    'qty_out': line.qty_plan - line.qty_out,
                    'work_from': line.work_from.id,
                    'work_to': line.work_to.id,
                    'check_id': line.id,
                    # 'qty_start': line.qty_plan
                })]
            })
            line.write({
                'qty_plan': line.qty_out
            })

    def _in_approve_with_confirm(self):
        self.ensure_one()
        for line in self.stock_transfer_line.filtered(lambda r: r.qty_in == 0):
            line.write({
                'qty_in': line.qty_out
            })
        self._action_in_approve()

    def action_in_approve(self):
        self.ensure_one()  # vì cần bật popup khi người dùng chọn không đủ số lượng
        if any(line.qty_in == 0 for line in self.stock_transfer_line):
            view = self.env.ref('forlife_stock.stock_transfer_popup_in_confirm_view_form')
            return {
                'name': 'Điều chuyển ngay?',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.transfer.popup.confirm',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': dict(self.env.context, default_stock_transfer_id=self.id),
            }
        return self._action_in_approve()

    def _action_in_approve(self):
        self.ensure_one()
        self._validate_product_tolerance('in')
        self.write({'state': 'done'})
        return self._action_in_approve_in_process()

    def _create_stock_picking(self, data, location_id, location_dest_id, stock_picking_type, origin, date_done):
        for data_line in data:
            data_line[2].update({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})
        stock_picking = self.env['stock.picking'].create({
            'transfer_id': self.id,
            'origin': origin,
            'date_done': date_done,
            'picking_type_id': stock_picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_ids_without_package': data,
        })
        stock_picking.button_validate()
        return stock_picking

    def _create_stock_picking_with_ho(self, data, location_id, location_dest_id, stock_picking_type, origin, date_done):
        location_ho = self.env.ref('forlife_stock.ho_location_stock')
        to_data = data
        for data_line in to_data:
            data_line[2].update({'location_id': location_id.id, 'location_dest_id': location_ho.id})
        stock_picking_to_ho = self.env['stock.picking'].create({
            'transfer_id': self.id,
            'origin': origin,
            'date_done': date_done,
            'picking_type_id': stock_picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_ho.id,
            'move_ids_without_package': to_data,
        })
        stock_picking_to_ho.button_validate()

        from_data = data
        for data_line in from_data:
            data_line[2].update({'location_id': location_ho.id, 'location_dest_id': location_dest_id.id})
        stock_picking_from_ho = self.env['stock.picking'].create({
            'transfer_id': self.id,
            'picking_type_id': stock_picking_type.id,
            'location_id': location_ho.id,
            'location_dest_id': location_dest_id.id,
            'move_ids_without_package': from_data,
        })
        stock_picking_from_ho.button_validate()

    def _action_in_approve_in_process(self):
        company_id = self.env.company.id
        pk_type = self.env['stock.picking.type'].sudo().search(
            [('company_id', '=', company_id), ('code', '=', 'internal')], limit=1)
        origin = self.name
        date_done = self.date_in_approve
        location_id = self.location_id
        location_dest_id = self.location_dest_id
        stock_picking_type = pk_type
        data = []
        diff_transfer = self.env['stock.transfer']
        for line in self.stock_transfer_line:
            product = line.product_id
            product_quantity = min(line.qty_in, line.qty_out)
            data.append((0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'date': datetime.now(),
                'product_uom': line.uom_id.id,
                'product_uom_qty': product_quantity,
                'quantity_done': product_quantity,
            }))
            if line.qty_in > line.qty_out:
                diff_transfer_data = [(0, 0, {
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'product_id': product.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': abs(line.qty_plan - product_quantity),
                    'qty_in': line.qty_in - line.qty_out,
                    'qty_out': line.qty_in - line.qty_out,
                })]
                diff_transfer |= self._create_diff_transfer(diff_transfer_data, state='in_approve', type='excess')
                line.write({
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'qty_plan': product_quantity,
                    'qty_out': product_quantity,
                    'qty_in': product_quantity,
                })
            elif line.qty_in < line.qty_out:
                diff_transfer_data = [(0, 0, {
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'product_id': product.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': abs(line.qty_plan - product_quantity),
                    'qty_in': line.qty_out - line.qty_in,
                    'qty_out': line.qty_out - line.qty_in,
                })]
                diff_transfer |= self._create_diff_transfer(diff_transfer_data, state='out_approve', type='lack')
                line.write({
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'qty_plan': product_quantity,
                    'qty_out': product_quantity,
                    'qty_in': product_quantity,
                })
        if location_id.warehouse_id.state_id.id == location_dest_id.warehouse_id.state_id.id:
            picking = self._create_stock_picking(data, location_id, location_dest_id, stock_picking_type, origin, date_done)
            # if picking.location_dest_id.id_deposit and picking.location_dest_id.account_stock_give:
            self._create_move_import_int(picking,location_id, location_dest_id)
        else:
            self._create_stock_picking_with_ho(data, location_id, location_dest_id, stock_picking_type, origin, date_done)
        self._create_stock_picking_other_import_and_export(data, location_id, location_dest_id)
        if diff_transfer:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'Có phiếu dở dang đã được tạo cần xác nhận!',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def _create_diff_transfer(self, data, state='draft', type=''):
        self.ensure_one()
        return self.env['stock.transfer'].create({
            'reference_document': self.name,
            'employee_id': self.employee_id.id,
            'document_type': 'excess_arising_lack_arise',
            'stock_request_id': self.stock_request_id.id,
            'type': type,
            'is_diff_transfer': True,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'work_from': self.work_from.id,
            'work_to': self.work_to.id,
            'stock_transfer_line': data,
            'production_order_id': self.production_order_id.id,
            'state': state,
        })

    def action_approve(self):
        for record in self:
            record.write({'state': 'approved',
                         # 'approval_logs_ids': [(0, 0, {
                         #     'request_approved_date': date.today(),
                         #     'approval_user_id': record.env.user.id,
                         #     'note': 'Approved',
                         #     'state': 'approved',
                         # })],
            })

    def action_reject(self):
        for record in self:
            record.write({'state': 'reject'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_done(self):
        for record in self:
            record.write({'state': 'done',
                         # 'approval_logs_ids': [(0, 0, {
                         #     'request_approved_date': date.today(),
                         #     'approval_user_id': record.env.user.id,
                         #     'note': 'Done',
                         #     'state': 'done',
                         # })],
            })

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            warehouse = self.env['stock.location'].browse(vals.get('location_id')).code
            vals['name'] = (self.env['ir.sequence'].next_by_code('stock.transfer.sequence') or 'PXB') + (
                warehouse if warehouse else '') + str(
                datetime.now().year)
        return super(StockTransfer, self).create(vals)

    def unlink(self):
        if any(item.state not in ('draft', 'cancel') for item in self):
            raise ValidationError("You only delete a record in draft or cancel status !!")
        return super(StockTransfer, self).unlink()

    @api.depends('location_id', 'location_dest_id')
    def _compute_document_type(self):
        for rec in self:
            if rec.location_id.id == rec.location_dest_id.id:
                rec.document_type = 'same_branch'
            else:
                rec.document_type = 'difference_branch'

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu phiếu điều chuyển'),
            'template': '/forlife_stock/static/src/xlsx/import_stock_transfer.xlsx?download=true'
        }]

class StockTransferLine(models.Model):
    _name = 'stock.transfer.line'
    _description = 'Stock Transfer Line'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', store=True)
    qty_plan = fields.Integer(string='Quantity Plan')
    qty_out = fields.Integer(string='Quantity Out', copy=False)
    qty_in = fields.Integer(string='Quantity In', copy=False)
    qty_start = fields.Integer(string='', compute='compute_qty_start', store=1)
    quantity_remaining = fields.Integer(string="Quantity remaining", compute='compute_quantity_remaining')
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")

    stock_transfer_id = fields.Many2one('stock.transfer', string="Stock Transfer")
    work_from = fields.Many2one('forlife.production', string="LSX From")
    work_to = fields.Many2one('forlife.production', string="LSX To")
    product_str_id = fields.Many2one('transfer.request.line')
    is_from_button = fields.Boolean(default=False)
    qty_plan_tsq = fields.Integer(default=0, string='Quantity Plan Tsq')
    is_parent_done = fields.Boolean(compute='compute_is_parent_done', store=True)
    check_id = fields.Integer(string="")

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.product_tmpl_id.uom_id.id

    # @api.constrains('qty_in', 'qty_out')
    # def constrains_qty_in(self):
    #     for rec in self:
            # if rec.qty_in == 0 or rec.qty_out == 0:
            #     raise ValidationError(_('You have not re-entered the actual inventory quantity. If you continue, the system will automatically default to the approved quantity !!'))
            # if rec.qty_in > rec.qty_plan:
            #     raise ValidationError(_('The number of inputs is greater than or equal to the number of adjustments !!'))
            # if rec.qty_out > rec.qty_plan:
            #     raise ValidationError(_('Output quantity is greater than or equal to the number of adjustments !!'))

    @api.depends('qty_plan', 'qty_in')
    def compute_quantity_remaining(self):
        for item in self:
            item.quantity_remaining = max(item.qty_plan - item.qty_in, 0)

    @api.depends('qty_plan', 'stock_transfer_id.state')
    def compute_qty_start(self):
        for item in self:
            if item.stock_transfer_id.state in ('draft', 'wait_approve'):
                item.qty_start = item.qty_plan

    @api.constrains('qty_plan', 'is_from_button', 'qty_plan_tsq')
    def constrains_qty_plan(self):
        for rec in self:
            if rec.is_from_button and (rec.qty_plan > rec.qty_plan_tsq):
                raise ValidationError(
                    _('Quantity plan cannot be larger than the quantity plan of the ticket !!'))

    def validate_product_quantity(self, location=False, is_diff_transfer=False):
        self.ensure_one()
        product = self.product_id
        stock_transfer_line = self.sudo().search([('id', '!=', self.id), ('product_id', '=', product.id), ('stock_transfer_id.location_id', '=', location.id), ('stock_transfer_id.state', 'in', ['out_approve', 'in_approve'])])
        product_quantity = self.qty_out + sum([line.qty_out for line in stock_transfer_line])
        result = product.with_context(default_detailed_type='product',
            location=location.id)._compute_quantities_dict(
            self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'),
            self._context.get('from_date'), self._context.get('to_date'))
        qty_available = result[product.id].get('qty_available', 0)
        quantity_prodution = self.env['quantity.production.order'].search(
            [('product_id', '=', product.id), ('location_id', '=', self.stock_transfer_id.location_id.id),
             ('production_id', '=', self.work_from.id)])
        quantity_prodution_to = self.env['quantity.production.order'].search(
            [('product_id', '=', product.id), ('location_id', '=', self.stock_transfer_id.location_dest_id.id),
             ('production_id', '=', self.work_to.id)])
        if self.work_from:
            if quantity_prodution:
                if self.qty_out > quantity_prodution.quantity:
                    raise ValidationError('Số lượng tồn kho sản phẩm %s trong lệnh sản xuất %s không đủ để điều chuyển!' % (product.name, self.work_from.code))
                else:
                    quantity_prodution.update({
                        'quantity': quantity_prodution.quantity - self.qty_out
                    })
            else:
                raise ValidationError('Sản phẩm %s không có trong lệnh sản xuất %s!' % (product.name, self.work_from.code))
            if self.work_to:
                if quantity_prodution_to:
                    quantity_prodution_to.update({
                        'quantity': quantity_prodution_to.quantity + self.qty_out
                    })
                else:
                    self.env['quantity.production.order'].create({
                        'product_id': product.id,
                        'location_id': self.stock_transfer_id.location_dest_id.id,
                        'production_id': self.work_to.id,
                        'quantity': self.qty_out
                    })
        else:
            if self.work_to:
                if quantity_prodution_to:
                    quantity_prodution_to.update({
                        'quantity': quantity_prodution_to.quantity + self.qty_out
                    })
                else:
                    self.env['quantity.production.order'].create({
                        'product_id': product.id,
                        'location_id': self.stock_transfer_id.location_dest_id.id,
                        'production_id': self.work_to.id,
                        'quantity': self.qty_out
                    })
        if qty_available < product_quantity:
            if is_diff_transfer:
                raise ValidationError('Số lượng tồn kho sản phẩm %s không đủ để tạo phiếu dở dang!' % product.name)
            else:
                raise ValidationError('Số lượng tồn kho sản phẩm %s không đủ để điều chuyển!' % product.name)
        # if self.work_from and self.qty_out > self.work_from.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == product.id).remaining_qty:
        #     raise ValidationError('Số lượng điều chuyển lớn hơn số lượng còn lại trong lệnh sản xuất!')

    def validate_product_tolerance(self, type='out'):
        self.ensure_one()
        product = self.product_id
        tolerance = product.tolerance
        if not self.stock_transfer_id.is_diff_transfer:
            quantity = self.qty_out if type == 'out' else self.qty_in
            if quantity > self.qty_plan * (1 + (tolerance / 100)):
                raise ValidationError('Sản phẩm %s không được nhập quá %s %% số lượng ban đầu' % (product.name, tolerance))
        else:
            start_transfer = self.env['stock.transfer'].search([('name', '=', self.stock_transfer_id.reference_document)], limit=1)
            other_transfer = self.env['stock.transfer'].search([('reference_document', '=', start_transfer.name)])
            quantity_old = sum([line.qty_out if type == 'out' else line.qty_in for line in other_transfer.stock_transfer_line.filtered(
                lambda r: r.product_id == self.product_id)])
            for rec in start_transfer.stock_transfer_line:
                if rec.product_id == self.product_id:
                    quantity = quantity_old + rec.qty_out if type == 'out' else quantity_old + rec.qty_in
                    if quantity > rec.qty_start * (1 + (tolerance / 100)):
                        raise ValidationError('Sản phẩm %s không được nhập quá %s %% số lượng ban đầu' % (product.name, tolerance))

    @api.depends('stock_transfer_id', 'stock_transfer_id.state')
    def compute_is_parent_done(self):
        for item in self:
            item.is_parent_done = True if item.stock_transfer_id and item.stock_transfer_id.state == 'done' else False


class ApprovalLogsStock(models.Model):
    _name = 'approval.logs.stock'
    _description = 'Approval Logs Stock'

    stock_transfer_id = fields.Many2one('stock.transfer', ondelete='cascade')
    stock_transfer_request_id = fields.Many2one('stock.transfer.request', ondelete='cascade')
    res_model = fields.Char('Resource Model')
    request_approved_date = fields.Date('Request Approved')
    approval_user_id = fields.Many2one('res.users')
    function = fields.Char(related='approval_user_id.function')  # Job Position in res.user
    note = fields.Text()
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'Draft'),
                   ('open', 'Open'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('done', 'Done')])
    state_request = fields.Selection(
        default='draft',
        string="Status Request",
        selection=[('draft', 'Draft'),
                   ('wait_confirm', 'Wait Confirm'),
                   ('approved', 'Approved'),
                   ('done', 'Done'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')])


class StockTransferPopupConfirm(models.TransientModel):
    _name = 'stock.transfer.popup.confirm'
    _description = 'Stock Transfer Popup Confirm'

    stock_transfer_id = fields.Many2one('stock.transfer')

    def process_out(self):
        self.ensure_one()
        self.stock_transfer_id._out_approve_with_confirm()

    def process_in(self):
        self.ensure_one()
        self.stock_transfer_id._in_approve_with_confirm()


class ForlifeProductionFinishedProduct(models.Model):
    _inherit = 'forlife.production.finished.product'

    forlife_production_stock_transfer_line_ids = fields.Many2many('stock.transfer.line')
    forlife_production_stock_move_ids = fields.Many2many('stock.move')
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_remaining_qty')

    # @api.depends('forlife_production_stock_transfer_line_ids', 'forlife_production_stock_transfer_line_ids.stock_transfer_id.state')
    def _compute_remaining_qty(self):
        for rec in self:
            qty_done = sum([line.quantity_done for line in rec.forlife_production_stock_move_ids.filtered(
                lambda r: r.picking_id.state in 'done')])
            rec.stock_qty = qty_done
            rec.remaining_qty = rec.produce_qty - qty_done


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
