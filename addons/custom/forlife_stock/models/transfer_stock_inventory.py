from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import json
from io import BytesIO
import xlsxwriter
import base64


class TransferStockInventory(models.Model):
    _name = 'transfer.stock.inventory'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Kiểm kê cân tồn kho'
    _rec_name = 'code'

    code = fields.Char(string="Code", default='New', copy=False)
    employee_id = fields.Many2one('hr.employee', string="User")
    location_id = fields.Many2one('stock.location', string='Location', domain="[('usage', 'in', ['internal'])]")
    note = fields.Text(string="Note")
    transfer_stock_inventory_line_ids = fields.One2many('transfer.stock.inventory.line', 'transfer_stock_inventory_id',
                                                        copy=True)
    x_classify = fields.Boolean('Phân loại hàng lỗi',copy=False)
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_confirm', 'Wait Confirm'),
                   ('approved', 'Done'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel')], default='draft', copy=False)
    reason_reject = fields.Text('Reason Reject')
    reason_cancel = fields.Text('Reason Cancel')
    is_nk_xk = fields.Boolean(default=False, copy=False)


    def action_import_other(self):
        for item in self:
            import_other = self.env['stock.picking'].search([('origin', '=', item.code), ('other_import', '=', True)])
            context = {'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('Nhập khác'),
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', import_other.ids)],
                'context': context
            }

    def action_export_other(self):
        for item in self:
            export_other = self.env['stock.picking'].search([('origin', '=', item.code), ('other_export', '=', True)])
            context = {'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('Xuất khác'),
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', export_other.ids)],
                'context': context
            }

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['create_date'] = datetime.now()
        return res

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('transfer.stock.inventory.name.sequence') or 'TSI'
        res = super(TransferStockInventory, self).create(vals)
        # if self._context.get('x_classify') and not res.x_classify:
        #     raise ValidationError('Giá trị xuất đang không khớp với giá trị nhập')
        return res

    def write(self, vals_list):
        res = super().write(vals_list)
        # if self._context.get('x_classify') and not self.x_classify:
        #     raise ValidationError('Giá trị xuất đang không khớp với giá trị nhập')
        return res

    def action_wait_confirm(self):
        for rec in self:
            for line in rec.transfer_stock_inventory_line_ids:
                number_product = self.env['stock.quant'].search(
                    [('location_id', '=', line.location_id.id), ('product_id', '=', line.product_from_id.id)])
                if not number_product or sum(number_product.mapped('quantity')) < line.qty_out:
                    raise ValidationError('Số lượng sản phẩm trong kho không đủ')
                elif (line.total_out != line.total_in):
                    raise ValidationError(
                        'Bạn không thể cân tồn giá trị xuất khác giá trị nhập')
            rec.write({'state': 'wait_confirm'})

    def action_approve(self):
        picking_type_in = self.env['stock.picking.type'].search([
            ('import_or_export', '=', 'other_import'),
            ('company_id', '=', self.env.company.id)], limit=1)
        if not picking_type_in:
            raise ValidationError(
                'Công ty: %s chưa được cấu hình kiểu giao nhận cho phiếu Nhập khác' % (self.env.user.company_id.name))
        picking_type_out = self.env['stock.picking.type'].search([
            ('import_or_export', '=', 'other_export'),
            ('company_id', '=', self.env.company.id)], limit=1)
        if not picking_type_out:
            raise ValidationError(
                'Công ty: %s chưa được cấu hình kiểu giao nhận cho phiếu Xuất khác' % (self.env.user.company_id.name))
        export_inventory_balance, enter_inventory_balance, export_inventory_balance_classify, import_inventory_balance_classify = self.get_location()
        for rec in self:
            data_ex_other = {}
            if not export_inventory_balance.x_property_valuation_in_account_id and not enter_inventory_balance.x_property_valuation_out_account_id:
                raise ValidationError(
                    'Nhập/Xuất cân đối tồn kho - tự kiểm kê chưa có tài khoản định giá tồn kho (xuất hàng)')
            for line in rec.transfer_stock_inventory_line_ids:
                key_import = (str(line.location_id), 'import')

                key_export = (str(line.location_id), 'export')
                if not self.x_classify:
                    if not enter_inventory_balance:
                        raise ValidationError(
                            "Công ty %s chưa được cấu hình lý do nhập khác xuất khác: Nhập cân đối tồn kho - tự kiểm kê với mã N201" % (self.env.user.company_id.name))
                    product_import = (
                        0, 0,
                        {'product_id': line.product_to_id.id, 'product_uom_qty': line.qty_in,
                         'product_uom': line.uom_to_id.id,
                         'name': line.product_to_id.name, 'price_unit': line.product_to_id.standard_price,
                         'location_id': enter_inventory_balance.id,
                         'location_dest_id': line.location_id.id,
                         "quantity_done": line.qty_in, 'work_production': line.mrp_production_to_id.id,
                         'amount_total': line.product_to_id.standard_price * line.qty_in
                         })
                else:
                    amount_total = -line.product_from_id._prepare_out_svl_vals(line.qty_out,
                                                                               line.location_id.company_id).get('value')
                    if not import_inventory_balance_classify:
                        raise ValidationError("Công ty %s chưa được cấu hình lý do nhập khác xuất khác: Nhập tách/Gộp mã hàng hóa với mã N402" % (self.env.user.company_id.name))
                    product_import = (
                        0, 0,
                        {'product_id': line.product_to_id.id, 'product_uom_qty': line.qty_in,
                         'product_uom': line.uom_to_id.id,
                         'name': line.product_to_id.name, 'price_unit': amount_total / line.qty_in,
                         'location_id': import_inventory_balance_classify.id,
                         'location_dest_id': line.location_id.id,
                         "quantity_done": line.qty_in, 'work_production': line.mrp_production_to_id.id,
                         'amount_total': amount_total
                         })
                if self.x_classify and (not export_inventory_balance_classify or not import_inventory_balance_classify):
                    raise ValidationError(
                        "Công ty %s chưa được cấu hình lý do nhập khác xuất khác mã X802 hoặc N402" % (
                            self.env.user.company_id.name))
                elif not self.x_classify and (not export_inventory_balance or not enter_inventory_balance):
                    raise ValidationError(
                        "Công ty %s chưa được cấu hình lý do nhập khác xuất khác có mã 1381000003 hoặc N201" % (
                            self.env.user.company_id.name))

                product_export = (
                    0, 0,
                    {'product_id': line.product_from_id.id, 'product_uom_qty': line.qty_out,
                     'product_uom': line.uom_from_id.id, 'name': line.product_from_id.name,
                     'price_unit': line.unit_price_from,
                     'location_id': line.location_id.id,
                     'location_dest_id': export_inventory_balance.id if not self.x_classify else export_inventory_balance_classify.id,
                     "quantity_done": line.qty_out, 'work_production': line.mrp_production_from_id.id,
                     'amount_total': line.total_out
                     })
                data_import = {
                    "name": picking_type_in.sequence_id.next_by_id(),
                    "is_locked": True,
                    "immediate_transfer": False,
                    'transfer_stock_inventory_id': rec.id,
                    'location_id': enter_inventory_balance.id if not self.x_classify else import_inventory_balance_classify.id,
                    'reason_type_id': self.env.ref('forlife_stock.reason_type_5').id,
                    'location_dest_id': line.location_id.id,
                    'scheduled_date': datetime.now(),
                    'origin': rec.code,
                    'other_import': True,
                    'state': 'assigned',
                    'picking_type_id': picking_type_in.id,
                    'move_ids_without_package': [product_import]
                }
                data_export = {
                    "name": picking_type_out.sequence_id.next_by_id(),
                    "is_locked": True,
                    "immediate_transfer": False,
                    'transfer_stock_inventory_id': rec.id,
                    'location_id': line.location_id.id,
                    'reason_type_id': self.env.ref('forlife_stock.reason_type_4').id,
                    'location_dest_id': export_inventory_balance.id if not self.x_classify else export_inventory_balance_classify.id,
                    'scheduled_date': datetime.now(),
                    'origin': rec.code,
                    'other_export': True,
                    'state': 'assigned',
                    'picking_type_id': picking_type_out.id,
                    'move_ids_without_package': [product_export]
                }
                number_product = self.env['stock.quant'].search(
                    [('location_id', '=', line.location_id.id), ('product_id', '=', line.product_from_id.id)])
                if not number_product or sum(number_product.mapped('quantity')) < line.qty_out:
                    raise ValidationError('Số lượng sản phẩm trong kho không đủ')
                else:
                    if data_ex_other.get(key_import):
                        data_ex_other.get(key_import).get('move_ids_without_package').append(product_import)
                        data_ex_other.get(key_export).get('move_ids_without_package').append(product_export)
                    else:
                        data_ex_other.update({
                            key_export: data_export,
                            key_import: data_import

                        })
            for item in data_ex_other:
                # self.create_picking_and_move(item,  data_ex_other)
                picking_id = self.env['stock.picking'].with_context({'skip_immediate': True}).create(
                    data_ex_other.get(item))
                picking_id.button_validate()
            rec.write({'state': 'approved', 'is_nk_xk': True})

    def get_location(self):
        export_inventory_balance = self.env['stock.location'].search(
            [('company_id', '=', self.env.company.id), ('code', '=', '1381000003')], limit=1)
        enter_inventory_balance = self.env['stock.location'].search(
            [('company_id', '=', self.env.company.id), ('code', '=', 'N201')], limit=1)
        export_inventory_balance_classify = self.env['stock.location'].search(
            [('company_id', '=', self.env.company.id), ('code', '=', 'X802')], limit=1)
        import_inventory_balance_classify = self.env['stock.location'].search(
            [('company_id', '=', self.env.company.id), ('code', '=', 'N402')], limit=1)
        return export_inventory_balance, enter_inventory_balance, export_inventory_balance_classify, import_inventory_balance_classify

    def create_picking_and_move(self, item, data_ex_other):
        if item[1] == 'export':
            picking_id = self.env['stock.picking'].with_context({'skip_immediate': True}).create(
                    data_ex_other.get(item))
            picking_id.button_validate()
        else:
            picking_id = self.env['stock.picking'].with_context({'skip_immediate': True}).create(
                data_ex_other.get(item))
            for line in picking_id.move_ids:
                journal_id = line._get_accounting_data_for_valuation()[0]
                credit = {
                    'product_id': line.product_id.id,
                    'name': picking_id.name + ': ' + line.product_id.name,
                    'ref': line.reference,
                    'quantity': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom_id': line.product_id.uom_id.id,
                    'account_id': picking_id.location_id.x_property_valuation_out_account_id.id,
                    'balance': - line.product_qty*line.price_unit
                }
                account_debit = line.product_id.categ_id.property_stock_valuation_account_id
                if not account_debit:
                    raise ValidationError(
                        'Sản phẩm: %s chưa được cấu tài khoản định giá tồn kho trong Danh mục sản phẩm' % (line.product_id.name))
                debit = {
                    'product_id': line.product_id.id,
                    'name': picking_id.name + ': ' + line.product_id.name,
                    'ref': line.reference,
                    'quantity': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom_id': line.product_id.uom_id.id,
                    'account_id': account_debit.id,
                    'balance': line.product_qty*line.price_unit
                }
                vals = {
                    'journal_id': journal_id,
                    'ref': picking_id.name + ' - ' + line.product_id.name,
                    'partner_id': picking_id.partner_id.id,
                    'move_type': 'entry',
                    'stock_move_id': line.id,
                    'line_ids': [(0, 0, credit), (0, 0, debit)],
                }
                invoice_id = self.env['account.move'].create(vals)
                invoice_id.action_post()
    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("Bạn không thể xóa bản ghi ngoài trạng thái nháp"))
        return super(TransferStockInventory, self).unlink()

    @api.constrains('transfer_stock_inventory_line_ids')
    def constrains_request_lines(self):
        for item in self:
            if not item.transfer_stock_inventory_line_ids:
                raise ValidationError(
                    _('Bạn chưa nhập sản phẩm'))


class TransferStockInventoryLine(models.Model):
    _name = "transfer.stock.inventory.line"

    transfer_stock_inventory_id = fields.Many2one('transfer.stock.inventory')
    product_from_id = fields.Many2one('product.product', string='Product From')
    uom_from_id = fields.Many2one('uom.uom', string='Uom', related='product_from_id.uom_id')
    qty_out = fields.Integer(string="Quantity Out")
    unit_price_from = fields.Float(string="Unit Price", related='product_from_id.list_price')
    total_out = fields.Float(string='Total Out', compute='compute_total_out')
    mrp_production_from_id = fields.Many2one('forlife.production', string="MRP production from ")
    product_to_id = fields.Many2one('product.product', string="Product To")
    uom_to_id = fields.Many2one('uom.uom', string='Uom', related='product_to_id.uom_id')
    location_id = fields.Many2one('stock.location', string='Location')
    qty_in = fields.Integer(string="Quantity In")
    unit_price_to = fields.Float(string="Unit Price", compute='compute_unit_price_to')
    total_in = fields.Float(string='Total In', compute='compute_total_in')
    mrp_production_to_id = fields.Many2one('forlife.production', string="MRP production to ")

    @api.depends('qty_out', 'unit_price_from')
    def compute_total_out(self):
        for item in self:
            item.total_out = item.qty_out * item.unit_price_from

    @api.depends('qty_in', 'unit_price_to')
    def compute_total_in(self):
        for item in self:
            item.total_in = item.qty_in * item.unit_price_to

    @api.depends('qty_in', 'unit_price_to', 'qty_out', 'product_to_id')
    def compute_unit_price_to(self):
        for r in self:
            if r.transfer_stock_inventory_id.x_classify:
                r.unit_price_to = r.qty_out * r.unit_price_from / r.qty_in if r.qty_in else 0
            elif r.product_to_id:
                r.unit_price_to = r.product_to_id.list_price
            else:
                r.unit_price_to = 0
