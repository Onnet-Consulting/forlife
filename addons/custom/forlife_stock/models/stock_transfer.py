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
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")
    employee_id = fields.Many2one('hr.employee', string="User", default=lambda self: self.env.user.employee_id.id, required=1)
    reference_document_id = fields.Many2one('stock.transfer.request', string="Transfer Request")
    production_order_id = fields.Many2one('production.order', string="Production Order")
    request_date = fields.Datetime(string="Request Date", default=datetime.now(), required=1)
    document_type = fields.Selection(
        string="Type",
        selection=[('same_branch', 'Same Branch'),
                   ('difference_branch', 'Difference Branch'),
                   ('excess_arising_lack_arise', 'Excess Arising/Lack Arise')], default='same_branch', required=1)
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
    stock_transfer_line = fields.One2many('stock.transfer.line', 'stock_transfer_id', copy=True)
    approval_logs_ids = fields.One2many('approval.logs.stock', 'stock_transfer_id')

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_wait_approve(self):
        for record in self:
            record.write({'state': 'wait_approve'})

    def action_out_approve(self):
        for record in self:
            record.write({'state': 'out_approve'})

    def action_in_approve(self):
        for record in self:
            record.write({'state': 'in_approve'})
        self.create_stock_picking()

    def create_stock_picking(self):
        for record in self:
            location_id = record.location_id
            location_warehouse_id = location_id.warehouse_id.id
            location_dest_id = record.location_dest_id
            stock_picking_type = self.env.ref('stock.picking_type_internal')
            data = []
            diff_transfer_data = []
            for line in record.stock_transfer_line:
                product = line.product_id
                product_quantity = min(line.qty_in, line.qty_out)
                result = product.with_context(default_detailed_type='product', location=location_id.id)._compute_quantities_dict(
                    self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'),
                    self._context.get('from_date'), self._context.get('to_date'))
                qty_available = result[product.id].get('qty_available', 0)
                if qty_available < product_quantity:
                    raise ValidationError('Số lượng tồn kho không đủ để điều chuyển!')
                data.append((0, 0, {
                    'product_id': product.id,
                    'name': product.display_name,
                    'date': datetime.now(),
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': product_quantity,
                    'quantity_done': product_quantity,
                }))
                if line.qty_in > line.qty_out:
                    diff_transfer_data.append((0, 0, {
                        'product_id': product.id,
                        'uom_id': line.uom_id.id,
                        'qty_plan': line.qty_in - line.qty_out,
                        'qty_out': 0,
                        'qty_in': line.qty_in - line.qty_out,
                    }))
                elif line.qty_in < line.qty_out:
                    diff_transfer_data.append((0, 0, {
                        'product_id': product.id,
                        'uom_id': line.uom_id.id,
                        'qty_plan': line.qty_out - line.qty_in,
                        'qty_out': line.qty_out - line.qty_in,
                        'qty_in': 0,
                    }))
            if location_id.warehouse_id.state_id.id == location_dest_id.warehouse_id.state_id.id:
                for data_line in data:
                    data_line[2].update({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})
                stock_picking = self.env['stock.picking'].create({
                    'transfer_id': record.id,
                    'picking_type_id': stock_picking_type.id,
                    'location_id': location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'move_ids_without_package': data,
                })
                stock_picking.button_validate()
            else:
                location_ho = self.env.ref('forlife_stock.ho_location_stock')
                to_data = data
                for data_line in to_data:
                    data_line[2].update({'location_id': location_id.id, 'location_dest_id': location_ho.id})
                stock_picking_to_ho = self.env['stock.picking'].create({
                    'transfer_id': record.id,
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
                    'transfer_id': record.id,
                    'picking_type_id': stock_picking_type.id,
                    'location_id': location_ho.id,
                    'location_dest_id': location_dest_id.id,
                    'move_ids_without_package': from_data,
                })
                stock_picking_from_ho.button_validate()
            if diff_transfer_data:
                self.env['stock.transfer'].create({
                    'employee_id': record.employee_id.id,
                    'document_type': 'excess_arising_lack_arise',
                    'stock_request_id': record.stock_request_id.id,
                    'is_diff_transfer': True,
                    'location_id': record.location_id.id,
                    'location_dest_id': record.location_dest_id.id,
                    'stock_transfer_line': diff_transfer_data,
                    'production_order_id': record.production_order_id.id,
                })

    def action_approve(self):
        for record in self:
            record.write({'state': 'approved',
                         'approval_logs_ids': [(0, 0, {
                             'request_approved_date': date.today(),
                             'approval_user_id': record.env.user.id,
                             'note': 'Approved',
                             'state': 'approved',
                         })],
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
                         'approval_logs_ids': [(0, 0, {
                             'request_approved_date': date.today(),
                             'approval_user_id': record.env.user.id,
                             'note': 'Done',
                             'state': 'done',
                         })],
            })

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.transfer.sequence') or 'ST'
        return super(StockTransfer, self).create(vals)

    def unlink(self):
        if any(item.state not in ('draft', 'cancel') for item in self):
            raise ValidationError("You only delete a record in draft or cancel status !!")
        return super(StockTransfer, self).unlink()


class StockTransferLine(models.Model):
    _name = 'stock.transfer.line'
    _description = 'Stock Transfer Line'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', store=True)
    qty_plan = fields.Integer(default=0, string='Quantity Plan')
    qty_out = fields.Integer(default=0, string='Quantity Out')
    qty_in = fields.Integer(default=0, string='Quantity In')
    quantity_remaining = fields.Integer(string="Quantity remaining", compute='compute_quantity_remaining')
    stock_request_id = fields.Many2one('stock.transfer.request', string="Stock Request")

    stock_transfer_id = fields.Many2one('stock.transfer', string="Stock Transfer")
    product_str_id = fields.Many2one('transfer.request.line')
    is_from_button = fields.Boolean(default=False)
    qty_plan_tsq = fields.Integer(default=0, string='Quantity Plan Tsq')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.product_tmpl_id.uom_id.id

    @api.constrains('qty_in', 'qty_out')
    def constrains_qty_in(self):
        for rec in self:
            if rec.qty_in > rec.qty_plan:
                raise ValidationError(_('The number of inputs is greater than or equal to the number of adjustments !!'))
            if rec.qty_out > rec.qty_plan:
                raise ValidationError(_('Output quantity is greater than or equal to the number of adjustments !!'))
                
    @api.depends('qty_plan', 'qty_in')
    def compute_quantity_remaining(self):
        for item in self:
            item.quantity_remaining = item.qty_plan - item.qty_in

    @api.constrains('qty_plan', 'is_from_button', 'qty_plan_tsq')
    def constrains_qty_plan(self):
        for rec in self:
            if rec.is_from_button and (rec.qty_plan > rec.qty_plan_tsq):
                raise ValidationError(
                    _('Quantity plan cannot be larger than the quantity plan of the ticket !!'))

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
