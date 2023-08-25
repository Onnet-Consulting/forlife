# import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
import math


class StockTransfer(models.Model):
    _name = 'stock.transfer'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Stock Transfer'
    _check_company_auto = True
    _order = "write_date desc"

    name = fields.code = fields.Char(string="Reference", default="New", copy=False)
    location_id = fields.Many2one('stock.location', string="Whs From", required=1)
    location_dest_id = fields.Many2one('stock.location', string="Whs To", required=1)
    work_from = fields.Many2one('forlife.production', string="LSX From",
                                domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    work_to = fields.Many2one('forlife.production', string="LSX To",
                              domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")
    employee_id = fields.Many2one('hr.employee', string="User", default=lambda self: self.env.user.employee_id.id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string="Phòng ban")
    reference_document_id = fields.Many2one('stock.transfer.request', string="Transfer Request")
    production_order_id = fields.Many2one('production.order', string="Production Order")
    create_date = fields.Datetime(string='Create Date', default=lambda self: fields.datetime.now())
    document_type = fields.Selection(
        string="Type",
        selection=[('same_branch', 'Same Branch'),
                   ('difference_branch', 'Difference Branch'),
                   ('excess_arising_lack_arise', 'Excess Arising/Lack Arise')], default='same_branch', required=1,
        compute='_compute_document_type')
    type = fields.Selection([
        ('excess', 'Điều chuyển phát sinh thừa'),
        ('lack', 'Điều chuyển phát sinh thiếu'),
    ], string='Type', copy=False)
    method_transfer = fields.Selection(
        string="Method",
        selection=[('transfer_between_warehouse', 'Transfer Between Warehouse'),
                   ('transfer_between_production_order', 'Transfer Between Production Order')],
        default='transfer_between_warehouse', required=1)
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
    is_diff_transfer = fields.Boolean(string="Diff Transfer", default=False, copy=False)
    stock_transfer_line = fields.One2many('stock.transfer.line', 'stock_transfer_id', copy=True, string='Chi tiết')
    total_package = fields.Float(string='Total Package (Number)')
    total_weight = fields.Float(string='Total Weight (Kg)')
    reference_document = fields.Char(copy=False)
    origin = fields.Char(copy=False)
    # approval_logs_ids = fields.One2many('approval.logs.stock', 'stock_transfer_id')
    note = fields.Text("Ghi chú")
    date_transfer = fields.Datetime("Ngày xác nhận xuất", default=datetime.now(), copy=False)
    date_in_approve = fields.Datetime("Ngày xác nhận nhập", default=datetime.now(), copy=False)
    is_need_scan_barcode = fields.Boolean(compute='_compute_need_scan_barcode', store=False)
    picking_count = fields.Integer(compute='_compute_picking_count')
    backorder_count = fields.Integer(compute='_compute_backorder_count')

    total_request_qty = fields.Float(string='Tổng số lượng điều chuyển', compute='_compute_total_qty')
    total_in_qty = fields.Float(string='Tổng số lượng xuất', compute='_compute_total_qty')
    total_out_qty = fields.Float(string='Tổng số lượng nhận', compute='_compute_total_qty')

    @api.depends('stock_transfer_line.qty_plan', 'stock_transfer_line.qty_in', 'stock_transfer_line.qty_out')
    def _compute_total_qty(self):
        for rec in self:
            self._cr.execute("""
                SELECT 
                    sum(stl.qty_plan) as qty_plan,
                    sum(stl.qty_in) as qty_in,
                    sum(stl.qty_out) as qty_out
                FROM stock_transfer_line stl where stock_transfer_id = %s;
            """ % rec.id)
            data = self._cr.dictfetchone()
            rec.total_request_qty = data.get('qty_plan', 0)
            rec.total_in_qty = data.get('qty_in', 0)
            rec.total_out_qty = data.get('qty_out', 0)

    def _compute_picking_count(self):
        for transfer in self:
            transfer.picking_count = self.env['stock.picking'].search_count([('transfer_id', '=', transfer.id)])

    def _compute_backorder_count(self):
        for transfer in self:
            transfer.backorder_count = self.env['stock.transfer'].search_count([('reference_document', '=', transfer.name)])

    @api.depends(
        'stock_transfer_line',
        'stock_transfer_line.product_id',
        'stock_transfer_line.product_id.is_need_scan_barcode'
    )
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = any(sm.product_id.is_need_scan_barcode for sm in rec.stock_transfer_line)

    def open_scan_barcode(self):
        self.ensure_one()
        stock_transfer_scan_line_ids = [(0, 0, {
                'transfer_line_id': stl.id,
                'max_qty': math.floor(((stl.qty_plan * (stl.product_id.tolerance + 100)) / 100)),
                'product_qty_done': stl.qty_out if self.state == 'approved' else stl.qty_in
            }) for stl in self.stock_transfer_line if stl.product_id.is_need_scan_barcode]
        if stock_transfer_scan_line_ids:
            scan_id = self.env['stock.transfer.scan'].create({
                'transfer_id': self.id,
                'stock_transfer_scan_line_ids': stock_transfer_scan_line_ids
            })
            return {
                'name': self.name,
                'view_mode': 'form',
                'res_model': 'stock.transfer.scan',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': scan_id.id
            }

    def action_view_picking(self):
        self.ensure_one()
        ctx = dict(self._context)
        picking_ids = self.env['stock.picking'].search([('transfer_id', '=', self.id)])
        return {
            'name': _('Phiếp nhập/xuất'),
            'domain': [('id', 'in', picking_ids.ids)],
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': ctx,
        }

    def action_view_backorder(self):
        self.ensure_one()
        ctx = dict(self._context)
        transfer_ids = self.env['stock.transfer'].search([('reference_document', '=', self.name)])
        return {
            'name': _('Phiếu điều chuyển'),
            'domain': [('id', 'in', transfer_ids.ids)],
            'res_model': 'stock.transfer',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': ctx,
        }

    def _check_qty_available(self):
        location_id = self.location_id
        work_from = self.work_from
        QuantityProductionOrder = self.env['quantity.production.order'].sudo()
        for line in self.stock_transfer_line:
            product = line.product_id
            domain = [('location_id', '=', location_id.id), ('product_id', '=', line.product_id.id)]
            if work_from:
                domain.append(('production_id.code', '=', work_from.code))
                qty_prod_order_ids = QuantityProductionOrder.search(domain)
                if qty_prod_order_ids:
                    total_qty_production = sum(x.quantity for x in qty_prod_order_ids)
                    if line.qty_out > total_qty_production:
                        raise ValidationError(
                            _("Số lượng xuất của sản phẩm '%s' vượt quá số lượng khả dụng trong lệnh sản xuất '%s'.") % (
                            product.name, work_from.name))
                else:
                    raise ValidationError(_("Không có tồn sản phẩm '%s' trong kho '%s' của lệnh sản xuất '%s'.") % (
                    product.name, location_id.name, work_from.name))
            else:
                qty_prod_order_ids = QuantityProductionOrder.search(domain)
                if qty_prod_order_ids:
                    total_qty_production = sum(x.quantity for x in qty_prod_order_ids)
                    result = product.with_context(default_detailed_type='product',
                                                  location=location_id.id)._compute_quantities_dict(None, None, None,
                                                                                                    None, None)
                    free_qty = result[product.id].get('free_qty', 0)
                    qty_real = free_qty - total_qty_production
                    if line.qty_out > qty_real:
                        raise ValidationError(_("Số lượng xuất của sản phẩm '%s' vượt quá số lượng khả dụng.") % (product.name))
                else:
                    raise ValidationError(_("Không có tồn sản phẩm '%s' trong kho '%s'.") % (
                        product.name, location_id.name))

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
        if self._context.get('skip_confirm'):
            return self._action_out_approve()
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
        # self._check_qty_available()
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
        if self.type == 'excess':
            self.write({'state': 'done'})

    def _update_forlife_production(self):
        for line in self.stock_transfer_line:
            if line.work_from:
                forlife_production_service_cost = line.work_from.forlife_production_finished_product_ids.filtered(
                    lambda r: r.product_id.id == line.product_id.id)
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
        if not self.env.user.has_group('forlife_permission_management.group_stock_transfer_can_be_scan'):
            for line in self.stock_transfer_line.filtered(lambda r: r.qty_out == 0 and not r.product_id.is_need_scan_barcode):
                line.write({
                    'qty_out': line.qty_plan
                })
        else:
            for line in self.stock_transfer_line.filtered(lambda r: r.qty_out == 0):
                line.write({
                    'qty_out': line.qty_plan
                })
        self._action_out_approve()

    def _out_approve_less_quantity(self, stock_transfer_line_less):
        self.ensure_one()
        line_data = []
        for line in stock_transfer_line_less:
            line_data.append((0, 0, {
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'qty_plan': line.qty_plan - line.qty_out,
                'qty_out': line.qty_plan - line.qty_out,
                'work_from': line.work_from.id,
                'work_to': line.work_to.id,
                'check_id': line.id,
                # 'qty_start': line.qty_plan
            }))
            line.write({
                'qty_plan': line.qty_out
            })

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
            'stock_transfer_line': line_data
        })

    def _in_approve_with_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group('forlife_permission_management.group_stock_transfer_can_be_scan'):
            for line in self.stock_transfer_line.filtered(lambda r: r.qty_in == 0 and not r.product_id.is_need_scan_barcode):
                line.write({
                    'qty_in': line.qty_out
                })
        else:
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
        company = self._check_location_mapping_with_comp(loc_id=location_id.id, loc_dest_id=location_dest_id.id, company=self.env.company)
        from_company = False
        to_company = False
        if company and not self._context.get('company_match', False):
            from_company = self.env.company.id
            to_company = company.id
        stock_picking = self.env['stock.picking'].create({
            'transfer_id': self.id,
            'origin': origin,
            'date_done': date_done,
            'picking_type_id': stock_picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_ids_without_package': data,
            'from_company': from_company,
            'to_company': to_company,
            'work_from': self.work_from.id or False,
            'work_to': self.work_to.id or False,
        })
        stock_picking.button_validate()
        return stock_picking

    def _check_location_mapping_with_comp(self, loc_id, loc_dest_id, company):
        if company.code == '1300':
            loc_map = self.env['stock.location.mapping'].sudo().search([('location_id', '=', loc_id)])
            loc_dest_map = self.env['stock.location.mapping'].sudo().search([('location_id', '=', loc_dest_id)])
            if loc_map:
                return loc_map.location_map_id.company_id
            if loc_dest_map:
                return loc_dest_map.location_map_id.company_id
        return False

    def _create_stock_picking_with_ho(self, data, location_id, location_dest_id, stock_picking_type, origin, date_done):
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id), ('code', '=', 'HO')], limit=1)
        if not warehouse_id:
            raise ValidationError("Hiện tại đang không có kho HO ở công ty %s. Vui lòng cấu hình trong Tồn kho -> Cấu hình -> Kho hàng với 'Tên viết tắt là HO'!" % self.env.company.name)
        if not warehouse_id.lot_stock_id:
            raise ValidationError("Vui lòng cấu hình 'Địa điểm Lưu trữ' trong kho %s" % warehouse_id.name)

        location_ho = warehouse_id.lot_stock_id
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
            'work_from': self.work_from.id or False,
            'work_to': self.work_to.id or False,
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
            'work_from': self.work_from.id or False,
            'work_to': self.work_to.id or False,
        })
        stock_picking_from_ho.button_validate()

    def _action_in_approve_in_process(self):
        if 'company_byside' in self._context and self._context.get('company_byside'):
            company_id = self.env['res.company'].sudo().search([('id', '=', self._context.get('company_byside'))])
        else:
            company_id = self.env.company
        pk_type = self.env['stock.picking.type'].sudo().search([('company_id', '=', company_id.id), ('code', '=', 'internal')], limit=1)
        origin = self.name
        date_done = self.date_in_approve
        location_id = self.location_id
        location_dest_id = self.location_dest_id
        stock_picking_type = pk_type
        data = []
        diff_transfer_data_in = []
        diff_transfer_data_out = []
        diff_transfer_in = self.env['stock.transfer']
        diff_transfer_out = self.env['stock.transfer']
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
                'work_from': line.work_from.id or False,
                'work_to': line.work_to.id or False,
            }))
            if line.qty_in > line.qty_out:
                diff_transfer_data_in.append((0, 0, {
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'product_id': product.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': 0,
                    'qty_in': line.qty_in - line.qty_out,
                    'qty_out': line.qty_in - line.qty_out,
                }))
                # diff_transfer |= self._create_diff_transfer(diff_transfer_data, state='in_approve', type='excess')
                line.write({
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'qty_plan': line.qty_plan,
                    'qty_out': product_quantity,
                    'qty_in': product_quantity,
                })
            elif line.qty_in < line.qty_out:
                diff_transfer_data_out.append((0, 0, {
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'product_id': product.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': abs(line.qty_plan - product_quantity),
                    'qty_in': line.qty_out - line.qty_in,
                    'qty_out': line.qty_out - line.qty_in,
                }))
                # diff_transfer |= self._create_diff_transfer(diff_transfer_data, state='out_approve', type='lack')
                line.write({
                    'product_str_id': line.product_str_id.id if line.product_str_id.id else False,
                    'qty_plan': product_quantity,
                    'qty_out': product_quantity,
                    'qty_in': product_quantity,
                })

        # Check state_id kho nguồn và kho đích
        warehouse_state_id = location_id.warehouse_id.state_id
        warehouse_dest_state_id = location_dest_id.warehouse_id.state_id
        if (warehouse_state_id.id == warehouse_dest_state_id.id) or (not warehouse_state_id and not warehouse_dest_state_id):
            self._create_stock_picking(data, location_id, location_dest_id, stock_picking_type, origin, date_done)
        else:
            # Trường hợp 2 kho khác cấu hình state (Tỉnh) trong cấu hình kho
            self._create_stock_picking_with_ho(data, location_id, location_dest_id, stock_picking_type, origin, date_done)

        self._create_stock_picking_other_import_and_export(data, location_id, location_dest_id)
        if not self._context.get('endloop') and self.env.company.code in ['1300', '1400']:
            self.with_context(endloop=True, company_match=self.env.company.id).create_tranfer_with_type_kigui()
        diff_transfer_in |= self._create_diff_transfer(diff_transfer_data_in, state='in_approve',
                                                       type='excess') if diff_transfer_data_in else diff_transfer_in
        diff_transfer_out |= self._create_diff_transfer(diff_transfer_data_out, state='out_approve',
                                                        type='lack') if diff_transfer_data_out else diff_transfer_out
        if diff_transfer_in or diff_transfer_out:
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
        self.write({
            'state': 'approved'
        })

    def action_reject(self):
        for record in self:
            record.write({'state': 'reject'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_done(self):
        self.write({
            'state': 'done'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                warehouse = self.env['stock.location'].browse(vals.get('location_id')).code
                vals['name'] = (self.env['ir.sequence'].next_by_code('stock.transfer.sequence') or 'PXB') + (warehouse if warehouse else '') + str(datetime.now().year)
            if vals.get('reference_document'):
                stock = self.env['stock.transfer'].search([('name', '=', vals.get('reference_document'))], limit=1)
                while stock and stock.reference_document:
                    stock = self.env['stock.transfer'].search([('name', '=', stock.reference_document)], limit=1)
                vals['origin'] = stock.name
            else:
                vals['origin'] = vals['name']
        return super(StockTransfer, self).create(vals_list)

    def unlink(self):
        if any(item.state not in ('draft') for item in self):
            raise ValidationError("Không thể xóa phiếu điều chuyển ở trạng thái khác dự thảo !!")
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
        }, {
            'label': _('Tải xuống mẫu phiếu import số lượng xuất điều chuyển'),
            'template': '/forlife_stock/static/src/xlsx/update_sl_xuat.xlsx?download=true'
        }, {
            'label': _('Tải xuống mẫu phiếu import số lượng nhập điều chuyển'),
            'template': '/forlife_stock/static/src/xlsx/update_sl_nhap.xlsx?download=true'
        }]

    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            if 'name' in fields and 'stock_transfer_line/sequence' in fields:
                product_codes = []
                query = """ 
                    SELECT pp.barcode 
                    FROM product_product pp
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    WHERE pp.is_need_scan_barcode = True
                """
                self._cr.execute(query)
                results = self._cr.dictfetchall()
                if results:
                    product_codes = [x['barcode'] for x in results]
                has_group_stock_transfer_can_be_scan = self.env.user.has_group('forlife_permission_management.group_stock_transfer_can_be_scan')
                for record in data:
                    # if not record[fields.index('name')]:
                    #     raise ValidationError(_("Thiếu giá trị bắt buộc cho trường mã phiếu"))
                    if not record[fields.index('stock_transfer_line/sequence')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường stt dòng"))
                    if 'stock_transfer_line/product_id' in fields and not record[fields.index('stock_transfer_line/product_id')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường sản phẩm"))
                    if 'stock_transfer_line/qty_out' in fields and not record[fields.index('stock_transfer_line/qty_out')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng xuất"))
                    if 'stock_transfer_line/qty_in' in fields and not record[fields.index('stock_transfer_line/qty_in')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng nhập"))
                    if record[fields.index('stock_transfer_line/product_id')] in product_codes and not has_group_stock_transfer_can_be_scan:
                        raise ValidationError(_("Sản phẩm %s bắt buộc quét barcode" % record[fields.index('stock_transfer_line/product_id')]))
                    # if 'date_in_approve' in fields and not record[fields.index('date_in_approve')]:
                    #     raise ValidationError(_("Thiếu giá trị bắt buộc cho trường ngày xác nhận nhập"))
                fields[fields.index('name')] = 'id'
                fields[fields.index('stock_transfer_line/sequence')] = 'stock_transfer_line/id'
                id = fields.index('id')
                line_id = fields.index('stock_transfer_line/id')
                product = fields.index('stock_transfer_line/product_id')
                reference = None
                for rec in data:
                    if rec[id]:
                        reference = rec[id]
                    stock = self.env['stock.transfer'].search([('name', '=', reference)], limit=1)
                    if not stock:
                        raise ValidationError(_("Không tồn tại mã phiếu %s" % (reference)))
                    if stock.state != 'out_approve' and 'stock_transfer_line/qty_in' in fields:
                        raise ValidationError(_("Phiếu %s chỉ có thể cập nhật số lượng nhập ở trạng thái xác nhận xuất" % (stock.name)))
                    if stock.state != 'approved' and 'stock_transfer_line/qty_out' in fields:
                        raise ValidationError(_("Phiếu %s chỉ có thể cập nhật số lượng xuất ở trạng thái đã phê duyệt" % (stock.name)))
                    if rec[id]:
                        rec[id] = stock.export_data(['id']).get('datas')[0][0]
                    if int(rec[line_id]) > len(stock.stock_transfer_line):
                        raise ValidationError(_("Phiếu %s không có dòng %s" % (stock.name, rec[line_id])))
                    elif rec[product] != stock.stock_transfer_line[int(rec[line_id]) - 1].product_id.barcode:
                        raise ValidationError(_("Mã sản phẩm của phiếu %s không khớp ở dòng %s" % (stock.name, rec[line_id])))
                    else:
                        rec[line_id] = \
                        stock.stock_transfer_line[int(rec[line_id]) - 1].export_data(['id']).get('datas')[0][0]
        return super().load(fields, data)

    def mass_export_confirmation(self):
        for rec in self:
            if rec.state != 'approved':
                msg = f"Phiếu điều chuyển %s không thể xác nhận xuất vì: Trạng thái khác Đã phê duyệt" % (rec.name)
                raise ValidationError(msg)
            try:
                rec._out_approve_with_confirm()
            except Exception as e:
                msg = f"Phiếu điều chuyển %s không thể xác nhận xuất vì: %s" % (rec.name, e.name)
                raise ValidationError(msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Xác nhận xuất thành công %s bản ghi' % len(self),
                'type': 'success',
                'sticky': False,
                'next': self.env.ref('forlife_stock.stock_transfer_action').read()[0],
            }
        }


class StockTransferLine(models.Model):
    _name = 'stock.transfer.line'
    _description = 'Stock Transfer Line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', store=True)
    qty_plan = fields.Float(string='Quantity Plan')
    qty_out = fields.Float(string='Quantity Out', copy=False)
    qty_in = fields.Float(string='Quantity In', copy=False)
    qty_start = fields.Float(string='', compute='compute_qty_start', store=1)
    quantity_remaining = fields.Float(string="Quantity remaining", compute='compute_quantity_remaining', copy=False)
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")

    stock_transfer_id = fields.Many2one('stock.transfer', string="Stock Transfer")
    work_from = fields.Many2one('forlife.production', string="LSX From",
                                domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    work_to = fields.Many2one('forlife.production', string="LSX To",
                              domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    product_str_id = fields.Many2one('transfer.request.line')
    is_from_button = fields.Boolean(default=False)
    qty_plan_tsq = fields.Float(default=0, string='Quantity Plan Tsq')
    is_parent_done = fields.Boolean(compute='compute_is_parent_done', store=True)
    check_id = fields.Integer(string="")
    sequence = fields.Integer(string="STT dòng")
    is_readonly_qty = fields.Boolean(default=False, compute='_compute_readonly_qty_in_out')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.product_tmpl_id.uom_id.id

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

    def _compute_readonly_qty_in_out(self):
        for r in self:
            if not self.env.user.has_group('forlife_permission_management.group_stock_transfer_can_be_scan') and r.product_id.is_need_scan_barcode:
                r.is_readonly_qty = True
            else:
                r.is_readonly_qty = False

    def validate_product_quantity(self, location=False, is_diff_transfer=False):
        self.ensure_one()
        QuantityProductionOrder = self.env['quantity.production.order']
        product = self.product_id
        stock_transfer_line = self.sudo().search([('id', '!=', self.id), ('product_id', '=', product.id),
                                                  ('stock_transfer_id.location_id', '=', location.id),
                                                  ('stock_transfer_id.state', 'in', ['out_approve', 'in_approve'])])
        product_quantity = self.qty_out + sum([line.qty_out for line in stock_transfer_line])
        # lấy tổng số lượng đang ở các trạng thái phiếu khác XN xuất, XN nhập và sl hiện có
        result = product.with_context(default_detailed_type='product',
                                      location=location.id)._compute_quantities_dict(
            self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'),
            self._context.get('from_date'), self._context.get('to_date'))
        qty_available = result[product.id].get('free_qty', 0)
        domain = [('product_id', '=', product.id), ('location_id', '=', self.stock_transfer_id.location_id.id)]
        
        if self.work_from:
            domain.append(('production_id.code', '=', self.work_from.code))
            if product.categ_id.category_type_id.code in ('2','3','4'):
                quantity_prodution = QuantityProductionOrder.search(domain, limit=1)
                if quantity_prodution:
                    if self.qty_out > quantity_prodution.quantity:
                        raise ValidationError(
                            '[04] - Số lượng tồn kho sản phẩm "%s" trong lệnh sản xuất "%s" không đủ để điều chuyển!' % (
                            product.name, self.work_from.code))
                    else:
                        quantity_prodution.update({
                            'quantity': quantity_prodution.quantity - self.qty_out
                        })
                else:
                    raise ValidationError('Sản phẩm [%s] %s không có trong lệnh sản xuất %s!' % (product.code, product.name, self.work_from.code))
            if self.work_to:
                if product.categ_id.category_type_id.code in ('2','3','4'):
                    quantity_prodution_to = QuantityProductionOrder.search(
                        [('product_id', '=', product.id), ('location_id', '=', self.stock_transfer_id.location_dest_id.id),
                        ('production_id.code', '=', self.work_to.code)])
                    if quantity_prodution_to:
                        quantity_prodution_to.update({
                            'quantity': quantity_prodution_to.quantity + self.qty_out
                        })
                    else:
                        QuantityProductionOrder.create({
                            'product_id': product.id,
                            'location_id': self.stock_transfer_id.location_dest_id.id,
                            'production_id': self.work_to.id,
                            'quantity': self.qty_out
                        })
        else:
            if product.categ_id.category_type_id.code in ('2','3','4'):
                qty_production_ids = QuantityProductionOrder.search(
                    [('product_id', '=', product.id), ('location_id', '=', self.stock_transfer_id.location_id.id)])
                if qty_production_ids:
                    qty_in_production = sum([x.quantity for x in qty_production_ids])
                    qty_free = qty_available - qty_in_production
                    if self.qty_out > qty_free:
                        raise ValidationError('Số lượng tồn kho sản phẩm %s không đủ để điều chuyển!' % (product.name))
                if self.work_to:
                    if quantity_prodution_to:
                        quantity_prodution_to.update({
                            'quantity': quantity_prodution_to.quantity + self.qty_out
                        })
                    else:
                        QuantityProductionOrder.create({
                            'product_id': product.id,
                            'location_id': self.stock_transfer_id.location_dest_id.id,
                            'production_id': self.work_to.id,
                            'quantity': self.qty_out
                        })
        if qty_available < product_quantity:
            if is_diff_transfer:
                raise ValidationError(
                    'Số lượng tồn kho sản phẩm [%s] %s không đủ để tạo phiếu dở dang!' % (product.code, product.name))
            else:
                raise ValidationError(
                    'Số lượng tồn kho sản phẩm [%s] %s không đủ để điều chuyển!' % (product.code, product.name))
        # if self.work_from and self.qty_out > self.work_from.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == product.id).remaining_qty:
        #     raise ValidationError('Số lượng điều chuyển lớn hơn số lượng còn lại trong lệnh sản xuất!')

    def validate_product_tolerance(self, type='out'):
        self.ensure_one()
        product = self.product_id
        tolerance = product.tolerance
        start_transfer = self.env['stock.transfer'].search([('id', '!=', self.stock_transfer_id.id), ('origin', '=', self.stock_transfer_id.origin)])
        if start_transfer:
            quantity_old = sum(
                [line.qty_out if type == 'out' else line.qty_in for line in start_transfer.stock_transfer_line.filtered(
                    lambda r: r.product_id == self.product_id)])
            quantity_plan = sum(
                [line.qty_plan for line in start_transfer.stock_transfer_line.filtered(
                    lambda r: r.product_id == self.product_id)])
            quantity = (quantity_old + self.qty_out) if type == 'out' else (quantity_old + self.qty_in)
            if quantity > (quantity_plan + self.qty_plan) * (1 + (tolerance / 100)):
                raise ValidationError('Sản phẩm [%s] %s không được nhập quá %s %% số lượng ban đầu' % (
                    product.default_code, product.name, tolerance))
        else:
            quantity = self.qty_out if type == 'out' else self.qty_in
            if quantity > self.qty_plan * (1 + (tolerance / 100)):
                raise ValidationError('Sản phẩm [%s] %s không được nhập quá %s %% số lượng ban đầu' % (
                    product.default_code, product.name, tolerance))

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
    remaining_qty = fields.Float(string='Còn lại', compute='_compute_remaining_qty',compute_sudo=True)

    # @api.depends('forlife_production_stock_transfer_line_ids', 'forlife_production_stock_transfer_line_ids.stock_transfer_id.state')
    def _compute_remaining_qty(self):
        for rec in self:
            qty_done = sum([line.quantity_done for line in rec.forlife_production_stock_move_ids.filtered(
                lambda r: r.picking_id.state in 'done')])
            rec.stock_qty = qty_done

            #Trường hợp nhập thừa thành phẩm
            remaining_qty = 0 if qty_done > rec.produce_qty else rec.produce_qty - qty_done
            rec.remaining_qty = remaining_qty


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if name and self._context.get('show_code_name'):
            return super().name_search(name, args, operator, limit)
        args = args or []
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
