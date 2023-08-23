from odoo import api, fields, models, _
from odoo.exceptions import UserError
from contextlib import contextmanager
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time
from odoo import Command
import re
import json


def check_length_255(val):
    if val:
        length = len(val)
        if length > 255:
            return False
        else:
            return True
    return False


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Char(string="Invoce Description")
    purchase_type = fields.Selection([
        ('product', 'Hàng hóa'),
        ('asset', 'Tài sản'),
        ('service', 'Dịch vụ'),
    ], string='PO Type', default='product')
    type_inv = fields.Selection([('tax', 'Nhập khẩu'), ('cost', 'Nội địa')], string='Loại hóa đơn')
    select_type_inv = fields.Selection(default='normal', copy=True, string="Loại hóa đơn", selection=[
        ('expense', 'Hóa đơn chi phí mua hàng'),
        ('labor', 'Hóa đơn chi phí nhân công'),
        ('normal', 'Hóa đơn chi tiết hàng hóa'),
    ])
    is_check_select_type_inv = fields.Boolean(default=False)
    number_bills = fields.Char(string='Number bills', copy=False)
    reference = fields.Char(string='Source Material')
    exchange_rate = fields.Float(string='Exchange Rate', default=1)
    accounting_date = fields.Datetime(string='Accounting Date')
    payment_status = fields.Char(string='Payment onchange_purchase_typestatus')
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    is_check_cost_view = fields.Boolean(string='Hóa đơn chi phí', compute='_compute_check_type_inv', store=1)
    is_check_cost_out_source = fields.Boolean(string='Hóa đơn chi phí thuê ngoài', compute='_compute_check_type_inv', store=1)
    is_check_invoice_tnk = fields.Boolean(default=False)
    ## sự thay đổi qua lại giữa các tab
    invoice_synthetic_ids = fields.One2many('account.move.line', 'move_id', domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))])
    exchange_rate_line_ids = fields.One2many('account.move.line', 'move_id', domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))])
    cost_total = fields.Float(string='Tổng chi phí')
    x_entry_types = fields.Selection(copy=True,
                                     string="Chi tiết loại bút toán custom",
                                     default='entry_normal',
                                     selection=[('entry_import_tax', 'Bút toán thuế nhập khẩu'),
                                                ('entry_special_consumption_tax', 'Bút toán thuế tiêu thụ đặc biệt'),
                                                ('entry_cost', 'Bút toán chi phí'),
                                                ('entry_cost_labor', 'Bút toán chi phí nhân công thuê ngoài/nội bộ'),
                                                ('entry_normal', 'Bút toán chi tiết hàng hóa'),
                                                ('entry_material', 'Bút toán nguyên phụ liệu'),
                                                ])
    product_expense_ids = fields.Many2many('product.product', string='Chi phí', compute='_compute_product_expense_labor_ids')

    # Chiết khấu tổng đơn
    trade_discount = fields.Float(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Float(string='Tổng chiết khấu thương mại')
    x_tax = fields.Float(string='Thuế VAT cùa chiết khấu(%)')
    x_amount_tax = fields.Float(string='Tiền VAT của chiết khấu', compute='compute_x_amount_tax', store=1, readonly=False)
    trade_tax_id = fields.Many2one('account.tax', string='Thuế VAT cùa chiết khấu(%)', domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]")

    # Chi phí
    transportation_total = fields.Float(string='Tổng chi phí vận chuyển')
    loading_total = fields.Float(string='Tổng chi phí bốc dỡ')
    custom_total = fields.Float(string='Tổng chi phí thông quan')
    payment_term_invoice = fields.Many2one('account.payment.term', string='Chính sách thanh toán')

    # field domain cho 2 field đơn mua hàng và phiếu nhập kho
    purchase_order_product_id = fields.Many2many('purchase.order', string='Purchase Order', copy=False)
    receiving_warehouse_id = fields.Many2many('stock.picking', copy=False)
    cost_line = fields.One2many('invoice.cost.line', 'invoice_cost_id', string='Invoice Cost Line', store=1)
    vendor_back_ids = fields.One2many('vendor.back', 'vendor_back_id', string='Vendor Back', store=1, readonly=False)
    # Field check k cho tạo addline khi hóa đơn đã có PO
    is_check = fields.Boolean()
    # lấy id để search ghi lại ref cho bút toán phát sinh
    e_in_check = fields.Integer(index=True)
    # todo: bỏ trường x_asset_fin sau golive. giữ lại để backup cho trường is_tc = true if x_asset_fin == 'TC'
    x_asset_fin = fields.Selection([('TC', 'TC'), ('QT', 'QT'),], string='Phân loại tài chính remove')
    is_tc = fields.Boolean('Phân loại tài chính', default=False)
    x_root = fields.Selection([('Intel', 'INT'), ('Winning', 'WIN'), ('other', 'Khác'),], string='Phân loại nguồn')
    domain_receiving_warehouse_id = fields.Char(compute='_compute_domain_receiving_warehouse_id', store=1)
    is_purchase_internal = fields.Boolean(compute='compute_is_purchase_internal')

    @api.depends('purchase_order_product_id')
    def compute_is_purchase_internal(self):
        for rec in self:
            rec.is_purchase_internal = bool(rec.purchase_order_product_id.filtered(lambda x: x.type_po_cost == 'cost'))

    @api.depends('cost_line', 'cost_line.product_id', 'account_expense_labor_detail_ids', 'account_expense_labor_detail_ids.product_id')
    def _compute_product_expense_labor_ids(self):
        for rec in self:
            if rec.select_type_inv == 'labor':
                rec.product_expense_ids = [(6, 0, rec.account_expense_labor_detail_ids.mapped('product_id').ids)]
            else:
                rec.product_expense_ids = [(6, 0, rec.cost_line.mapped('product_id.id'))]

    @api.depends('total_trade_discount', 'trade_tax_id', 'trade_discount')
    def compute_x_amount_tax(self):
        for rec in self:
            if rec.total_trade_discount != 0 and rec.trade_tax_id:
                rec.x_amount_tax = rec.trade_tax_id.amount / 100 * rec.total_trade_discount

    @api.constrains('x_tax')
    def constrains_x_tax(self):
        for rec in self:
            if rec.x_tax > 100 or rec.x_tax < 0:
                raise UserError(_('Bạn khổng thể nhập % thuế VAT của chiết khấu nhỏ hơn 0 hoặc lớn hơn 100!'))

    @api.onchange('cost_line.vnd_amount')
    def onchange_cost_line_vnd_amount(self):
        self.cost_total = sum(self.cost_line.mapped('vnd_amount'))

    @api.onchange('is_check_cost_view')
    def _onchange_is_check_cost_view(self):
        if self.is_check_cost_view and self.is_check_cost_out_source:
            self.is_check_cost_out_source = False

    @api.onchange('is_check_cost_out_source')
    def _onchange_is_check_cost_out_source(self):
        if self.is_check_cost_view and self.is_check_cost_out_source:
            self.is_check_cost_view = False

    def view_move_entry(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all")
        context = {'search_default_move_id': self.id, 'search_default_posted': 1}
        return dict(action, context=context)

    @api.onchange('partner_id', 'partner_id.group_id')
    def onchange_partner_id(self):
        if self.partner_id.group_id:
            if self.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_2').id:
                self.type_inv = 'cost'
            if self.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id:
                self.type_inv = 'tax'
        if not self.partner_id.property_purchase_currency_id:
            self.currency_id = self.env.company.currency_id

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            if self.type_inv != 'cost':
                self.exchange_rate = self.currency_id.inverse_rate
            else:
                self.exchange_rate = 1

    @api.depends('purchase_order_product_id')
    def _compute_domain_receiving_warehouse_id(self):
        for rec in self:
            if rec.purchase_order_product_id:
                picking_ids = rec.purchase_order_product_id.mapped('picking_ids').filtered(lambda x: x.state == 'done').ids
            else:
                picking_ids = ()
            rec.domain_receiving_warehouse_id = json.dumps([('id', 'in', tuple(picking_ids))])

    @api.onchange('purchase_order_product_id')
    def onchange_purchase_order_product_id(self):
        if self.purchase_order_product_id:
            picking_ids = self.purchase_order_product_id.mapped('picking_ids').filtered(lambda x: x.state == 'done')
            if picking_ids:
                self.receiving_warehouse_id = [(6, 0, picking_ids.ids)]
            else:
                self.receiving_warehouse_id = False
        else:
            self.receiving_warehouse_id = False

    @api.depends('select_type_inv')
    def _compute_check_type_inv(self):
        for rec in self:
            if rec.select_type_inv == 'expense':
                rec.is_check_cost_view = True
                rec.is_check_cost_out_source = False
            if rec.select_type_inv == 'labor':
                rec.is_check_cost_out_source = True
                rec.is_check_cost_view = False
            if rec.select_type_inv == 'normal':
                rec.is_check_cost_out_source = rec.is_check_cost_view = False

    def _prepare_account_expense_labor_detail(self, product_expense, price_subtotal):
        vals = {
            'move_id': self.id,
            'product_id': product_expense.id,
            'description': product_expense.name,
            'uom_id': product_expense.uom_id.id,
            'qty': 1,
            'price_subtotal_back': price_subtotal,
            'origin_currency_id': self.currency_id.id,
            'origin_price_subtotal_back': price_subtotal
        }
        return vals

    def _prepare_sum_expense_labor_value(self, product):
        vals = {
            'move_id': self.id,
            'product_id': product.id,
            'description': product.name,
            'uom_id': product.uom_id.id
        }
        return vals

    def insert_data(self):
        self.ensure_one()
        if not self.receiving_warehouse_id:
            raise ValidationError('Vui lòng chọn phiếu Nhập kho!')
        purchase_order_id = self.purchase_order_product_id or self.receiving_warehouse_id.purchase_id
        AccountMoveLine = self.env['account.move.line']
        AccountExpenseLaborDetail = self.env['account.expense.labor.detail']
        SummaryExpenseLaborAccount = self.env['summary.expense.labor.account']
        type_po_cost = purchase_order_id.mapped('type_po_cost')[0] if purchase_order_id.mapped('type_po_cost') else False

        if self.select_type_inv == 'normal' and purchase_order_id:
            currency_id = purchase_order_id[0].currency_id.id if purchase_order_id else False
            exchange_rate = purchase_order_id[0].exchange_rate if purchase_order_id else 1
        else:
            currency_id = self.currency_id.id or False
            exchange_rate = self.exchange_rate or 0

        self.write({
            'invoice_line_ids': False,
            'type_inv': type_po_cost if type_po_cost else False,
            'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') or type_po_cost else False,
            'exchange_rate': exchange_rate,
            'currency_id': currency_id,
            'invoice_date': datetime.now(),
            'reference': ', '.join(purchase_order_id.mapped('name')) if purchase_order_id else '',
            'is_check_select_type_inv': True,
            'account_expense_labor_detail_ids': False,
            'sum_expense_labor_ids': False,
            'cost_line': False,
            'purchase_order_product_id': [(6, 0, purchase_order_id.ids)],
        })
        picking_ids = self.receiving_warehouse_id
        pending_section = None
        if not self.partner_id:
            raise ValidationError('Vui lòng chọn Nhà cung cấp!')
        if not self.purchase_order_product_id:
            raise ValidationError('Vui lòng chọn ít nhất 1 Đơn mua hàng!')
        #  nếu tạo hoá đơn chi phí
        if self.select_type_inv == 'expense':
            picking_in_ids = picking_ids.filtered(lambda x: not x.x_is_check_return)
            if not picking_in_ids:
                raise UserError(_('Vui lòng chọn ít nhất 1 phiếu nhập kho để lên hóa đơn. Vui lòng kiểm tra lại!'))

            vals_lst = []
            cost_line_vals = []

            if not purchase_order_id.cost_line:
                raise UserError(_('Không có thông tin ở Tab Chi phí để lên hóa đơn. Vui lòng kiểm tra lại!'))

            total_amount_po = sum(purchase_order_id.order_line.mapped('total_vnd_amount'))
            for cost_line in purchase_order_id.cost_line:
                cost_actual_from_po = 0

                # luồng hóa đơn chi phí
                for po_line in purchase_order_id.order_line:
                    move_ids = po_line.move_ids.filtered(lambda x: x.picking_id in picking_ids and x.state == 'done')
                    move_return_ids = move_ids.mapped('returned_move_ids').filtered(lambda x: x.state == 'done' and x.picking_id in picking_ids)

                    # SL trên đơn PO
                    product_qty = po_line.product_qty
                    # lấy tổng SL hoàn thành trừ tổng SL trả của 1 dòng purchase order line
                    move_qty = sum(move_ids.mapped('quantity_done')) - sum(move_return_ids.mapped('quantity_done'))

                    amount_pol = po_line.total_vnd_amount
                    if not total_amount_po or not product_qty or move_qty <= 0:
                        return
                    cost_actual = (((amount_pol / total_amount_po) * cost_line.vnd_amount) * move_qty) / product_qty
                    cost_actual_from_po += cost_actual

                    # cost_actual_currency = round(cost_line.currency_id._convert(cost_actual, self.currency_id, self.company_id, self.date, round=False))

                    data = purchase_order_id._prepare_invoice_expense(cost_line, po_line, cost_actual)
                    if po_line.display_type == 'line_section':
                        pending_section = po_line
                        continue
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line()
                        line_vals.update(data)
                        line_vals.update({'move_id': self.id})
                        vals_lst.append(line_vals)
                        pending_section = None
                    line_vals = po_line._prepare_account_move_line()
                    line_vals.update(data)
                    line_vals.update({'move_id': self.id})
                    vals_lst.append(line_vals)

                # chuẩn bị dữ liệu tab chi phí
                data = cost_line.copy_data({'cost_line_origin': cost_line.id})[0]
                if 'purchase_order_id' in data:
                    del data['purchase_order_id']
                if 'actual_cost' in data:
                    del data['actual_cost']

                data.update({
                    'vnd_amount': cost_actual_from_po,
                    'invoice_cost_id': self.id
                })
                cost_line_vals.append(data)
            aml_ids = AccountMoveLine.create(vals_lst)

            product_expenses = []
            products = []
            for aml_id in aml_ids:
                if aml_id.product_expense_origin_id not in product_expenses:
                    product_expenses.append(aml_id.product_expense_origin_id)

                if aml_id.product_id not in products:
                    products.append(aml_id.product_id)

            # tạo dữ liệu chi tiết hóa đơn custom
            if product_expenses:
                expense_lst = []
                for product_expense in product_expenses:
                    sum_product_expense_moves = aml_ids.filtered(lambda x: x.product_expense_origin_id == product_expense)
                    price_subtotal = sum(sum_product_expense_moves.mapped('price_unit'))
                    expense_vals = self._prepare_account_expense_labor_detail(product_expense, price_subtotal)
                    expense_lst.append(expense_vals)
                expense_ids = AccountExpenseLaborDetail.create(expense_lst)

            # tạo dữ liệu tổng hợp
            if products:
                product_lst = []
                for product in products:
                    product_vals = self._prepare_sum_expense_labor_value(product)
                    product_lst.append(product_vals)
                sum_expense_ids = SummaryExpenseLaborAccount.create(product_lst)

            # tạo dữ liệu tab chi phí
            if cost_line_vals:
                invoice_cl_ids = self.env['invoice.cost.line'].create(cost_line_vals)

        elif self.select_type_inv == 'labor':
            labor_cost_ids = purchase_order_id.order_line_production_order.purchase_order_line_material_line_ids.filtered(lambda x: x.product_id.x_type_cost_product == 'labor_costs')
            if not labor_cost_ids:
                raise UserError(_('Đơn mua không có Chi phí nhân công và nguyên phụ liệu!'))
            vals_lst = []
            for labor_cost_id in labor_cost_ids:
                pol_id = labor_cost_id.purchase_order_line_id

                move_ids = pol_id.move_ids.filtered(lambda x: x.picking_id in picking_ids and x.state == 'done')
                move_return_ids = move_ids.mapped('returned_move_ids').filtered(lambda x: x.state == 'done')

                # lấy tổng SL hoàn thành trừ tổng SL trả của 1 dòng purchase order line
                move_qty = sum(move_ids.mapped('quantity_done')) - sum(move_return_ids.mapped('quantity_done'))

                if not pol_id.product_qty or move_qty <= 0:
                    return

                data_line = purchase_order_id._prepare_invoice_labor(labor_cost_id, move_qty)
                if pol_id.display_type == 'line_section':
                    pending_section = pol_id
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update(data_line)
                    line_vals.update({'move_id': self.id})
                    pending_section = None
                    vals_lst.append(line_vals)
                line_vals = pol_id._prepare_account_move_line()
                line_vals.update(data_line)
                line_vals.update({'move_id': self.id})
                vals_lst.append(line_vals)
            aml_ids = AccountMoveLine.create(vals_lst)

            product_labors = []
            products = []
            for aml_id in aml_ids:
                if aml_id.product_expense_origin_id not in product_labors:
                    product_labors.append(aml_id.product_expense_origin_id)

                if aml_id.product_id not in products:
                    products.append(aml_id.product_id)

            # tạo dữ liệu chi tiết hóa đơn custom
            if product_labors:
                labor_lst = []
                for product_labor in product_labors:
                    sum_product_labor_moves = aml_ids.filtered(
                        lambda x: x.product_expense_origin_id == product_labor)
                    price_subtotal = sum([x.price_unit for x in sum_product_labor_moves])
                    labor_vals = self._prepare_account_expense_labor_detail(product_labor, price_subtotal)
                    labor_lst.append(labor_vals)
                labor_ids = AccountExpenseLaborDetail.create(labor_lst)

            # tạo dữ liệu tổng hợp
            if products:
                product_lst = []
                for product in products:
                    product_vals = self._prepare_sum_expense_labor_value(product)
                    product_lst.append(product_vals)
                sum_expense_ids = SummaryExpenseLaborAccount.create(product_lst)
        else:
            self.prepare_move_line_type_invoice_product(purchase_order_id)

    def prepare_move_line_type_invoice_product(self, purchase_order_id):
        vals_lst = []
        sequence = 10
        AccountMoveLine = self.env['account.move.line']
        pending_section = None
        picking_ids = self.receiving_warehouse_id.filtered(lambda x: x.state == 'done' and not x.x_is_check_return)
        if not picking_ids:
            raise ValidationError('Vui lòng chọn ít nhất 1 phiếu nhập kho!')
        return_picking_ids = self.receiving_warehouse_id.filtered(lambda x: x.state == 'done' and x.x_is_check_return)
        for line in purchase_order_id.order_line:
            stock_move_ids = picking_ids.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id and x.state == 'done')
            for move_id in stock_move_ids.filtered(lambda x: x.quantity_done - x.qty_invoiced - x.qty_to_invoice - x.qty_refunded > 0):
                data_line = purchase_order_id._prepare_invoice_normal(line, move_id)
                qty_returned = sum(move_id.returned_move_ids.filtered(lambda x: x.state == 'done' and x.picking_id.id in return_picking_ids.ids).mapped('quantity_done'))
                quantity = move_id.quantity_done - move_id.qty_invoiced - move_id.qty_to_invoice - qty_returned
                if quantity <= 0:
                    continue
                move_id.qty_to_invoice = quantity
                move_id.qty_refunded = qty_returned
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update(data_line)
                    line_vals.update({
                        'quantity': quantity,
                        'quantity_purchased': quantity / line_vals['exchange_quantity'],
                        'sequence': sequence,
                        'move_id': self.id,
                    })
                    pending_section = None
                    vals_lst.append(line_vals)
                    sequence += 1

                line_vals = line._prepare_account_move_line()
                line_vals.update(data_line)
                line_vals.update({
                    'quantity': quantity,
                    'quantity_purchased': quantity / line_vals['exchange_quantity'],
                    'sequence': sequence,
                    'move_id': self.id,
                })
                vals_lst.append(line_vals)
                sequence += 1
        if not vals_lst:
            raise ValidationError('Tất cả phiếu nhập đã được lên hóa đơn, vui lòng kiểm tra lại')
        aml_ids = AccountMoveLine.create(vals_lst)

    @api.onchange('receiving_warehouse_id', 'select_type_inv')
    def onchange_invoice_line_ids_by_type(self):
        for rec in self:
            rec.invoice_line_ids = False
            rec.account_expense_labor_detail_ids = False
            rec.sum_expense_labor_ids = False
            if rec.select_type_inv == 'service':
                rec.purchase_type = 'service'
            else:
                rec.purchase_type = 'product'

            # Khi chọn picking nhập kho -> tự động add picking xuất kho
            if rec.receiving_warehouse_id:
                picking_id = rec.receiving_warehouse_id[-1]
                if not picking_id.x_is_check_return:
                    picking_return_id = self.env['stock.picking'].search([('relation_return', '=', picking_id.name), ('x_is_check_return', '=', True)])
                    rec.receiving_warehouse_id |= picking_return_id

    @api.constrains('invoice_line_ids', 'invoice_line_ids.total_vnd_amount')
    def constrains_total_vnd_amount(self):
        invoice_relationship = self.search(
            [('purchase_order_product_id', 'in', self.purchase_order_product_id.ids),
             ('purchase_type', '=', 'service')])
        for rec in self:
            if rec.purchase_type == 'service':
                reference = []
                for item in rec.purchase_order_product_id:
                    reference.append(item.name)
                    ref_join = ', '.join(reference)
                if sum(invoice_relationship.invoice_line_ids.mapped('total_vnd_amount')) > sum(rec.purchase_order_product_id.order_line.mapped('total_vnd_amount')):
                    raise ValidationError(
                        _('Tổng tiền của các hóa đơn dịch vụ đang là %s lớn hơn tổng tiền của đơn mua hàng dịch vụ %s liên quan là %s!')
                        % (sum(invoice_relationship.invoice_line_ids.mapped('total_vnd_amount')), ref_join,
                           sum(rec.purchase_order_product_id.order_line.mapped('total_vnd_amount'))))

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for rec in self:
            if 'vendor_back_ids' in vals:
                tax_line_ids = rec.line_ids.filtered(lambda x: x.display_type == 'tax')
                tax_line_ids.unlink()
                invoice_description = []
                for vendor_back_id in rec.vendor_back_ids:
                    if vendor_back_id.invoice_description not in invoice_description:
                        invoice_description.append(vendor_back_id.invoice_description)
                tax_lines = []
                for product in invoice_description:
                    backs = rec.vendor_back_ids.filtered(lambda x: x.invoice_description == product)
                    if backs:
                        tax_lines = rec._prepare_tax_line_to_expense_invoice(backs, product)
                        sum_price_subtotal_back = sum(backs.mapped('price_subtotal_back'))
                        sum_tax_back = sum(backs.mapped('tax_back'))
                        expense_detail = rec.account_expense_labor_detail_ids.filtered(lambda x: x.product_id == product)
                        if expense_detail:
                            expense_detail.write({
                                'price_subtotal_back': sum_price_subtotal_back,
                                'tax_back': sum_tax_back
                            })
                        invoice_lines = rec.invoice_line_ids.filtered(lambda x: x.product_expense_origin_id == product)
                        sum_price = sum(invoice_lines.mapped('price_unit'))
                        for invoice_line in invoice_lines:
                            invoice_line.write({
                                'price_unit': (sum_price_subtotal_back * invoice_line.price_unit) / sum_price if sum_price > 0 else 0,
                            })

                #Update các chi phí k được nhập ở Tab
                expense_invalid_detail = rec.account_expense_labor_detail_ids.filtered(lambda x: x.product_id not in invoice_description)
                if expense_invalid_detail:
                    expense_invalid_detail.write({
                        'price_subtotal_back': 0,
                        'tax_back': 0
                    })

                invoice_invalid_lines = rec.invoice_line_ids.filtered(lambda x: x.product_expense_origin_id not in invoice_description).unlink()

                # Thêm line thuế
                if tax_lines:
                    rec.write({
                        'line_ids': tax_lines
                    })
            # Update lại tài khoản với những line có sản phẩm
            if rec.select_type_inv in ('labor', 'expense') and rec.purchase_type == 'product':
                for line in rec.invoice_line_ids.filtered(lambda x: x.product_id and x.display_type == 'product' and x.account_id.id != line.product_id.categ_id.with_company(line.company_id).property_stock_account_input_categ_id.id):
                    line.write({
                        'account_id': line.product_id.categ_id.with_company(line.company_id).property_stock_account_input_categ_id.id,
                        'name': line.product_id.name
                    })

            ### ghi key search bút toán liên quan cho invocie:
            entry_relation_ship_id = self.search([('move_type', '=', 'entry'), ('e_in_check', '=', str(rec.id)),])
            if not entry_relation_ship_id:
                continue
            else:
                for line in entry_relation_ship_id:
                    line.write({
                        'ref': f"{str(rec.name)} - {str(line.invoice_description)}",
                    })
        return res

    # Dữ liệu Thuế cho hóa đơn chi phí mua hàng
    def _prepare_tax_line_to_expense_invoice(self, vendor_backs, product_id):
        tax_lines = []
        for back_id in vendor_backs:
            if back_id.tax_percent:
                price_unit = back_id.price_subtotal_back * self.exchange_rate
                taxes = back_id.tax_percent.compute_all(price_unit, quantity=1, currency=self.currency_id, product=product_id, partner=self.partner_id, is_refund=False, )
                if taxes.get('taxes') and taxes.get('taxes')[0]:
                    tax = taxes.get('taxes')[0]
                    tax_lines.append((0, 0, {
                        'name': tax['name'],
                        'tax_ids': [(6, 0, tax['tax_ids'])],
                        'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                        'balance': tax['amount'],
                        'debit': tax['amount'],
                        'credit': 0,
                        'account_id': tax['account_id'] or False,
                        'amount_currency': tax['amount'],
                        'tax_amount': tax['amount'],
                        'tax_base_amount': tax['base'],
                        'tax_repartition_line_id': tax['tax_repartition_line_id'],
                        'group_tax_id': tax['group'] and tax['group'].id or False,
                        'display_type': 'tax'
                    }))
        return tax_lines

    @api.constrains('exchange_rate', 'trade_discount')
    def constrains_exchange_rare(self):
        for item in self:
            if item.exchange_rate < 0:
                raise ValidationError('Tỷ giá không được âm!')
            if item.trade_discount < 0:
                raise ValidationError('Chiết khấu thương mại không được âm!')

    @api.onchange('trade_discount')
    def onchange_total_trade_discount(self):
        if self.trade_discount:
            if self.tax_totals.get('amount_untaxed') and self.tax_totals.get('amount_untaxed') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_untaxed') * (self.trade_discount / 100)

    @api.onchange('total_trade_discount')
    def onchange_trade_discount(self):
        if self.total_trade_discount:
            if self.tax_totals.get('amount_untaxed') and self.tax_totals.get('amount_untaxed') != 0:
                self.trade_discount = self.total_trade_discount / self.tax_totals.get('amount_untaxed') * 100


    def create_invoice_tnk_db(self):
        account_db = []
        account_tnk = []
        is_in = self.move_type in ('in_invoice', 'in_receipt')
        if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(self.company_id).property_stock_account_input_categ_id \
                or not self.env.ref('forlife_purchase.product_import_tax_default').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế nhập khẩu hoặc tài khoản chi phí kế toán của sản phẩm có tên là 'Thuế nhập khẩu'")
        if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(self.company_id).property_stock_account_input_categ_id \
                or not self.env.ref('forlife_purchase.product_excise_tax_default').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế tiêu thụ đặc biệt hoặc tài khoản chi phí kế toán của sản phẩm có tên là 'Thuế tiêu thụ đặc biệt'")
        for item in self.exchange_rate_line_ids:
            if item.amount_tax > 0:
                account_credit_tnk = (0, 0, {
                    'sequence': 99991,
                    'product_id': item.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').with_company(
                        self.company_id).property_account_expense_id.id,
                    'name': self.env.ref('forlife_purchase.product_import_tax_default').with_company(
                        self.company_id).property_account_expense_id.name,
                    'debit': 0 if is_in else item.amount_tax,
                    'credit': item.amount_tax if is_in else 0.0,
                })
                account_debit_tnk = (0, 0, {
                    'sequence': 9,
                    'product_id': item.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(
                        self.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.amount_tax if is_in else 0.0,
                    'credit': 0 if is_in else item.amount_tax,
                })
                lines_tnk = [account_debit_tnk, account_credit_tnk]
                account_tnk.extend(lines_tnk)
            if item.special_consumption_tax_amount > 0:
                account_credit_db = (0, 0, {
                    'sequence': 99991,
                    'product_id': item.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        self.company_id).property_account_expense_id.id,
                    'name': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        self.company_id).property_account_expense_id.name,
                    'debit': 0 if is_in else item.special_consumption_tax_amount,
                    'credit': item.special_consumption_tax_amount if is_in else 0,
                })
                account_debit_db = (0, 0, {
                    'sequence': 9,
                    'product_id': item.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(self.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.special_consumption_tax_amount if is_in else 0,
                    'credit': 0 if is_in else item.special_consumption_tax_amount,
                })
                lines_db = [account_debit_db, account_credit_db]
                account_db.extend(lines_db)
            merged_records_tnk = {}
            merged_records_db = {}
            for tnk in account_tnk:
                key = (tnk[2]['account_id'], tnk[2]['name'], tnk[2]['sequence'])
                if key in merged_records_tnk:
                    merged_records_tnk[key]['debit'] += tnk[2]['debit']
                    merged_records_tnk[key]['credit'] += tnk[2]['credit']
                else:
                    merged_records_tnk[key] = {
                        'sequence': tnk[2]['sequence'],
                        'account_id': tnk[2]['account_id'],
                        'product_id': tnk[2]['product_id'],
                        'name': tnk[2]['name'],
                        'debit': tnk[2]['debit'],
                        'credit': tnk[2]['credit'],
                    }
            for db in account_db:
                key = (db[2]['account_id'], db[2]['name'], db[2]['sequence'])
                if key in merged_records_db:
                    merged_records_db[key]['debit'] += db[2]['debit']
                    merged_records_db[key]['credit'] += db[2]['credit']
                else:
                    merged_records_db[key] = {
                        'sequence': db[2]['sequence'],
                        'account_id': db[2]['account_id'],
                        'product_id': db[2]['product_id'],
                        'name': db[2]['name'],
                        'debit': db[2]['debit'],
                        'credit': db[2]['credit'],
                    }
            # Chuyển đổi từ điển thành danh sách bản ghi
        merged_records_list_tnk = [(0, 0, record) for record in merged_records_tnk.values()]
        merged_records_list_db = [(0, 0, record) for record in merged_records_db.values()]
        if merged_records_list_db:
            invoice_db = self.create({
                'e_in_check': self.id,
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': f"Thuế tiêu thụ đặc biệt",
                'line_ids': merged_records_list_db,
                'move_type': 'entry',
            })
            invoice_db.action_post()
        if merged_records_list_tnk:
            invoice_tnk = self.create({
                'e_in_check': self.id,
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': "Thuế nhập khẩu",
                'line_ids': merged_records_list_tnk,
                'move_type': 'entry',
            })
            invoice_tnk.action_post()

    def create_tax_vat(self):
        account_vat = []
        is_in = self.move_type in ('in_invoice', 'in_receipt')
        if not self.env.ref('forlife_purchase.product_vat_tax').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản chi phí kế toán thuế VAT (Nhập khẩu), trong sản phẩm có tên là Thuế VAT (Nhập khẩu) ở tab kế toán")
        if not self.env.ref('forlife_purchase.product_vat_tax').categ_id.with_company(self.company_id).property_stock_account_input_categ_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục sản phẩm có tên là Thuế VAT (Nhập khẩu)")
        for line in self.exchange_rate_line_ids:
            if line.vat_tax_amount > 0:
                account_credit_vat = (0, 0, {
                    'sequence': 9,
                    'product_id': line.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_vat_tax').with_company(
                        self.company_id).property_account_expense_id.id,
                    'name': 'thuế giá trị gia tăng nhập khẩu (VAT)',
                    'debit': 0 if is_in else line.vat_tax_amount,
                    'credit': line.vat_tax_amount if is_in else 0.0,
                })
                account_debit_vat = (0, 0, {
                    'sequence': 99991,
                    'product_id': line.product_id.id,
                    'account_id': self.env.ref('forlife_purchase.product_vat_tax').categ_id.with_company(
                        self.company_id).property_stock_account_input_categ_id.id,
                    'name': line.name,
                    'debit': line.vat_tax_amount if is_in else 0.0,
                    'credit': 0 if is_in else line.vat_tax_amount,
                })
                lines_vat = [account_credit_vat, account_debit_vat]
                account_vat.extend(lines_vat)
            merged_records_vat = {}
            for db in account_vat:
                key = (db[2]['account_id'], db[2]['name'], db[2]['sequence'])
                if key in merged_records_vat:
                    merged_records_vat[key]['debit'] += db[2]['debit']
                    merged_records_vat[key]['credit'] += db[2]['credit']
                else:
                    merged_records_vat[key] = {
                        'sequence': db[2]['sequence'],
                        'account_id': db[2]['account_id'],
                        'name': db[2]['name'],
                        'debit': db[2]['debit'],
                        'credit': db[2]['credit'],
                    }
                # Chuyển đổi từ điển thành danh sách bản ghi
        merged_records_list_vat = [(0, 0, record) for record in merged_records_vat.values()]
        if merged_records_list_vat:
            invoice_vat = self.create({
                'e_in_check': self.id,
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': "Thuế giá trị gia tăng VAT (Nhập khẩu)",
                'line_ids': merged_records_list_vat,
                'move_type': 'entry',
            })
            invoice_vat.action_post()

    def create_trade_discount(self):
        self.ensure_one()
        is_in = self.move_type in ('in_invoice', 'in_receipt')
        account_expense_id = self.env.ref('forlife_purchase.product_discount_tax').with_company(self.company_id).property_account_expense_id
        if not account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản chi phí ở tab kế toán trong danh sản phẩm có tên là Chiết khấu tổng đơn!!")
        account_tax_id = self.trade_tax_id.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').account_id
        if not account_tax_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản trong phần Thuế!!")
        if not self.partner_id.property_account_payable_id:
            raise ValidationError(_("Bạn chưa cấu hình tài khoản phải trả ở tab kế toán trong nhà cung cấp %s") % self.partner_id.name)
        invoice_ck = self.create({
            'e_in_check': self.id,
            'partner_id': self.partner_id.id,
            'ref': f"{self.name} Chiết khấu tổng đơn",
            'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') else False,
            'invoice_date': self.invoice_date,
            'invoice_description': f"Hóa đơn chiết khấu tổng đơn",
            'move_type': 'entry',
            'purchase_order_product_id': self.purchase_order_product_id,
            'x_root': self.x_root,
            'is_tc': self.is_tc,
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': self.partner_id.property_account_payable_id.id,
                    'name': self.partner_id.property_account_payable_id.name,
                    'debit': (self.total_trade_discount + self.x_amount_tax) * self.exchange_rate if is_in else 0.0,
                    'credit': 0 if is_in else (self.total_trade_discount + self.x_amount_tax) * self.exchange_rate,
                }),
                (0, 0, {
                    'account_id': account_expense_id.id,
                    'name': account_expense_id.name,
                    'debit': 0 if is_in else self.total_trade_discount * self.exchange_rate,
                    'product_id': self.env.ref('forlife_purchase.product_discount_tax').id,
                    'credit': self.total_trade_discount * self.exchange_rate if is_in else 0.0,
                }),
                (0, 0, {
                    'account_id': account_tax_id.id,
                    'name': account_tax_id.name,
                    'debit': 0 if is_in else self.x_amount_tax * self.exchange_rate,
                    'credit': self.x_amount_tax * self.exchange_rate if is_in else 0.0,
                })
            ]
        })
        invoice_ck._post()
        return invoice_ck

    def action_post(self):
        for rec in self:
            if (rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id or rec.type_inv == 'tax') and rec.move_type != 'out_invoice':
                if rec.exchange_rate_line_ids:
                    rec.create_invoice_tnk_db()
                    rec.create_tax_vat()
            if rec.total_trade_discount:
                rec.create_trade_discount()
        res = super(AccountMove, self).action_post()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    cost_id = fields.Char('')
    text_check_cp_normal = fields.Char('')
    po_id = fields.Char('')
    stock_move_id = fields.Many2one('stock.move', copy=False)
    ware_name = fields.Char('')
    type = fields.Selection(related="product_id.product_type", string='Loại mua hàng')
    work_order = fields.Many2one('forlife.production', string='Work Order')
    warehouse = fields.Many2one('stock.location', string='Whs')
    discount_value = fields.Float(string='Chiết khấu', digits='Discount', default=0.0)
    tax_amount = fields.Monetary(string='Thuế', compute='_compute_tax_amount', store=1)

    # fields common !!
    production_order = fields.Many2one('forlife.production', string='Production order')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    occasion_code_id = fields.Many2one('occasion.code', string="Mã vụ việc")
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")

    # asset invoice!!
    asset_code = fields.Many2one('assets.assets', string=_('Asset code'))
    asset_name = fields.Char('Mô tả tài sản cố định')
    code_tax = fields.Char(string='Mã số thuế')
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")
    purchase_uom = fields.Many2one('uom.uom', string='Đơn vị mua')

    # field check readonly discount and discount_percent:
    readonly_discount = fields.Boolean(default=False)
    readonly_discount_value = fields.Boolean(default=False)

    # field check exchange_quantity khi ncc vãng lại:
    is_check_exchange_quantity = fields.Boolean(default=False)

    # field check vendor_price khi ncc vãng lại:
    is_passersby = fields.Boolean(related='move_id.is_passersby')
    is_red_color = fields.Boolean(compute='compute_vendor_price_ncc', store=1)

    # goods invoice!!
    promotions = fields.Boolean(string='Promotions', default=False)
    quantity_purchased = fields.Integer(string='Quantity Purchased', default=1)
    exchange_quantity = fields.Float(string='Exchange Quantity', default=1)
    request_code = fields.Char('Mã phiếu yêu cầu')
    vendor_price = fields.Float(string='Giá nhà cung cấp',
                                compute='compute_vendor_price_ncc',
                                store=1)
    total_vnd_amount = fields.Monetary('Tổng tiền VNĐ',
                                    compute='_compute_total_vnd_amount',
                                    store=1)
    total_vnd_exchange = fields.Monetary('Thành tiền VND',
                                      compute='_compute_total_vnd_amount',
                                      store=1)
    #field tab tnk:
    import_tax = fields.Float(string='% Thuế nhập khẩu')
    amount_tax = fields.Float(string='Tiền thuế nhập khẩu', compute='_compute_amount_tax', store=1, readonly=0)
    special_consumption_tax = fields.Float(string='% Thuế tiêu thụ đặc biệt')
    special_consumption_tax_amount = fields.Float(string='Thuế tiêu thụ đặc biệt', compute='_compute_special_consumption_tax_amount', store=1, readonly=0)
    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='Thuế GTGT', compute='_compute_vat_tax_amount', store=1, readonly=0)
    total_tax_amount = fields.Float(string='Tổng tiền thuế', compute='compute_total_tax_amount', store=1, readonly=0)
    # field tab tổng hợp:
    before_tax = fields.Float(string='Chi phí trước tính thuế',
                              compute='_compute_before_tax',
                              store=0)
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)',
                             compute='_compute_after_tax',
                             store=0)
    total_product = fields.Float(string='Tổng giá trị tiền hàng',
                                 compute='_compute_total_product',
                                 store=0)
    company_currency = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    # asset invoice!!
    asset_name = fields.Char('Mô tả tài sản cố định')
    code_tax = fields.Char(string='Mã số thuế')
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")
    purchase_uom = fields.Many2one('uom.uom', string='Purchase UOM')
    is_check_exchange_quantity = fields.Boolean(default=False)
    # field check vendor_price khi ncc vãng lại:
    is_passersby = fields.Boolean(related='move_id.is_passersby')
    is_red_color = fields.Boolean(compute='compute_vendor_price_ncc', store=1)

    @api.onchange('asset_code')
    def onchange_asset_code(self):
        if self.asset_code:
            self.asset_name = self.asset_code.name
            if not self.get_product_code():
                self.product_id = None
                self.name = None
                return {'domain': {'product_id': [('id', '=', 0)],
                                   'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                  ('company_id', '=', self.company_id.id)]
                                   }}
        else:
            return {'domain': {'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                              ('company_id', '=', self.company_id.id)]}}

    def get_product_code(self):
        account = self.asset_code.asset_account.id
        product_categ_id = self.env['product.category'].search([('property_account_expense_categ_id', '=', account)])
        if not product_categ_id:
            raise UserError(
                _('Không có nhóm sản phẩm nào cấu hình Tài khoản chi phí là %s' % self.asset_code.asset_account.code))
        product_id = self.env['product.product'].search([('categ_id', 'in', product_categ_id.ids)])
        if not product_id:
            product_categ_name = ','.join(product_categ_id.mapped('display_name'))
            raise UserError(_('Không có sản phẩm nào cấu hình nhóm sản phẩm là %s' % product_categ_name))
        if len(product_id) == 1:
            self.product_id = product_id
            return True
        else:
            product_names = ','.join(product_id.mapped('display_name'))
            raise UserError(_('Các sản phẩm cùng cấu hình %s. Vui lòng kiểm tra lại!' % product_names))

    @api.onchange('price_unit')
    def onchange_price_unit_set_discount(self):
        if self.price_unit and self.discount > 0:
            self.discount_value = (self.price_unit * self.quantity) * (self.discount / 100)

    def _get_stock_valuation_layers_price_unit(self, layers):
        price_unit_by_layer = {}
        for layer in layers:
            if layer.quantity != 0:
                price_unit_by_layer[layer] = layer.value / layer.quantity
            else:
                price_unit_by_layer[layer] = layer.unit_cost
        return price_unit_by_layer

    @api.constrains('product_uom_id')
    def _check_product_uom_category_id(self):
        for line in self:
            if line.move_id.select_type_inv in ('labor', 'expense', 'service'):
                pass
            else:
                if line.product_uom_id and line.product_id and line.product_uom_id.category_id != line.product_id.product_tmpl_id.uom_id.category_id:
                    raise UserError(_(
                        "The Unit of Measure (UoM) '%s' you have selected for product '%s', "
                        "is incompatible with its category : %s.",
                        line.product_uom_id.name,
                        line.product_id.name,
                        line.product_id.product_tmpl_id.uom_id.category_id.name
                    ))

    @api.constrains('import_tax', 'special_consumption_tax', 'vat_tax')
    def constrains_per(self):
        for item in self:
            if item.import_tax < 0:
                raise ValidationError('% thuế nhập khẩu phải >= 0 !')
            if item.special_consumption_tax < 0:
                raise ValidationError('% thuế tiêu thụ đặc biệt phải >= 0 !')
            if item.vat_tax < 0:
                raise ValidationError('% thuế GTGT >= 0 !')

    @api.depends('total_vnd_exchange', 'import_tax')
    def _compute_amount_tax(self):
        for rec in self:
            rec.amount_tax = rec.total_vnd_exchange * rec.import_tax / 100

    @api.depends('amount_tax', 'special_consumption_tax')
    def _compute_special_consumption_tax_amount(self):
        for rec in self:
            if rec.amount_tax == rec.total_vnd_exchange * rec.import_tax / 100:
                rec.special_consumption_tax_amount = (rec.total_vnd_exchange + rec.amount_tax) * rec.special_consumption_tax / 100

    @api.depends('special_consumption_tax_amount', 'vat_tax')
    def _compute_vat_tax_amount(self):
        for rec in self:
            if rec.special_consumption_tax_amount == (rec.total_vnd_exchange + (rec.total_vnd_exchange * rec.import_tax / 100)) * rec.special_consumption_tax / 100:
                rec.vat_tax_amount = (rec.total_vnd_exchange + rec.amount_tax + rec.special_consumption_tax_amount) * rec.vat_tax / 100

    @api.depends('vat_tax_amount')
    def compute_total_tax_amount(self):
        for rec in self:
            rec.total_tax_amount = rec.amount_tax + rec.special_consumption_tax_amount + rec.vat_tax_amount

    @api.depends('price_subtotal', 'move_id.exchange_rate', 'move_id')
    def _compute_total_vnd_amount(self):
        for rec in self:
            rec.total_vnd_amount = rec.price_subtotal * rec.move_id.exchange_rate
            rec.total_vnd_exchange = rec.total_vnd_amount + rec.before_tax

    @api.depends('move_id.cost_line.is_check_pre_tax_costs', 'total_vnd_amount')
    def _compute_before_tax(self):
        for rec in self:
            rec.before_tax = 0
            cost_line_true = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            for line in rec.move_id.invoice_line_ids:
                total_cost_true = 0
                if cost_line_true and line.total_vnd_amount > 0:
                    for item in cost_line_true:
                        before_tax = line.total_vnd_amount / sum(rec.move_id.invoice_line_ids.mapped('total_vnd_amount')) * item.vnd_amount
                        total_cost_true += before_tax
                        line.before_tax = total_cost_true
                    line.total_vnd_exchange = line.total_vnd_amount + line.before_tax
                else:
                    if line.before_tax != 0:
                        line.total_vnd_exchange = line.total_vnd_amount + line.before_tax
                    else:
                        line.total_vnd_exchange = line.total_vnd_amount

    @api.depends('move_id.cost_line.is_check_pre_tax_costs', 'move_id.exchange_rate_line_ids')
    def _compute_after_tax(self):
        for rec in self:
            rec.after_tax = 0
            cost_line_false = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            for line in rec.move_id.invoice_line_ids:
                total_cost = 0
                sum_vnd_amount = sum(rec.move_id.exchange_rate_line_ids.mapped('total_vnd_exchange'))
                sum_tnk = sum(rec.move_id.exchange_rate_line_ids.mapped('tax_amount'))
                sum_db = sum(rec.move_id.exchange_rate_line_ids.mapped('special_consumption_tax_amount'))
                if rec.move_id.type_inv == 'tax' and cost_line_false and line.total_vnd_exchange > 0:
                    for item in cost_line_false:
                        if sum_vnd_amount + sum_tnk + sum_db > 0:
                            total_cost += (line.total_vnd_exchange + line.tax_amount + line.special_consumption_tax_amount) / (sum_vnd_amount + sum_tnk + sum_db) * item.vnd_amount
                            line.after_tax = total_cost
                else:
                    line.after_tax = 0

    @api.depends('total_vnd_amount', 'before_tax', 'tax_amount', 'special_consumption_tax_amount', 'after_tax')
    def _compute_total_product(self):
        for record in self:
            record.total_product = record.total_vnd_amount + record.before_tax + record.tax_amount + record.special_consumption_tax_amount + record.after_tax

    @api.depends('exchange_quantity', 'quantity', 'product_id', 'purchase_uom',
                 'move_id.partner_id', 'move_id.partner_id.is_passersby', 'move_id', 'move_id.currency_id')
    def compute_vendor_price_ncc(self):
        today = datetime.now().date()
        for rec in self:
            if rec.move_id.purchase_type == 'product':
                if not (rec.product_id and rec.move_id.partner_id and rec.purchase_uom and rec.move_id.currency_id):
                    rec.is_red_color = False
                    continue
                data = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id),
                    ('partner_id', '=', rec.move_id.partner_id.id),
                    ('currency_id', '=', rec.move_id.currency_id.id),
                    ('amount_conversion', '=', rec.exchange_quantity),
                    ('product_uom', '=', rec.purchase_uom.id),
                    ('date_start', '<=', today),
                    ('date_end', '>=', today)
                ])
                rec.is_red_color = True if rec.exchange_quantity not in data.mapped('amount_conversion') else False
                if rec.product_id and rec.move_id.partner_id and rec.purchase_uom and rec.move_id.currency_id and not rec.is_red_color and not rec.move_id.partner_id.is_passersby:
                    closest_quantity = None  # Khởi tạo giá trị biến tạm
                    for line in data:
                        if rec.quantity and rec.quantity >= line.min_qty:
                            ### closest_quantity chỉ được cập nhật khi rec.quantity lớn hơn giá trị hiện tại của line.min_qty
                            if closest_quantity is None or line.min_qty > closest_quantity:
                                closest_quantity = line.min_qty
                                rec.vendor_price = line.price
                                rec.exchange_quantity = line.amount_conversion
            else:
                pass

    @api.depends('display_type', 'company_id')
    def _compute_account_id(self):
        res = super()._compute_account_id()
        for line in self:
            if line.move_id.purchase_type == 'product' and line.product_id and line.move_id.purchase_order_product_id and line.move_id.purchase_order_product_id[0].is_inter_company == False:
                line.account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                line.name = line.product_id.name
        return res

    @api.onchange('vendor_price')
    def onchange_vendor_price(self):
        if self.exchange_quantity != 0:
            self.price_unit = self.vendor_price / self.exchange_quantity
        else:
            self.price_unit = self.vendor_price

    @api.onchange('quantity_purchased', 'exchange_quantity')
    def onchange_quantity_purchased(self):
        self.quantity = self.quantity_purchased * self.exchange_quantity

    @api.onchange('quantity', 'exchange_quantity')
    def onchange_quantity(self):
        if self.exchange_quantity > 0:
            self.quantity_purchased = self.quantity / self.exchange_quantity
        if self.stock_move_id:
            self.stock_move_id.qty_to_invoice = self.quantity
            qty_returned = sum(self.stock_move_id.returned_move_ids.filtered(lambda x: x.state == 'done').mapped('quantity_done'))
            if self.quantity_purchased > (self.stock_move_id.quantity_done - self.stock_move_id.qty_invoiced - qty_returned) / (self.exchange_quantity or 1):
                qty_in = (self.stock_move_id.quantity_done - self.stock_move_id.qty_invoiced - qty_returned) / (self.exchange_quantity or 1)
                raise ValidationError(_('Số lượng vượt quá số lượng mua hoàn thành nhập kho (%s)!' % str(qty_in)))

    @api.model_create_multi
    def create(self, list_vals):
        for line in list_vals:
            is_check_invoice_tnk = self.env['account.move'].browse(line.get('move_id')).is_check_invoice_tnk
            is_check_cost_view = self.env['account.move'].browse(line.get('move_id')).is_check_cost_view
            if line.get('account_id') == self.env.ref('l10n_vn.1_chart1331').id:
                if is_check_cost_view:
                    list_vals.remove(line)
                if is_check_invoice_tnk:
                    list_vals.remove(line)
        res = super().create(list_vals)
        return res


    # sửa lại base odoo để ăn theo tỉ giá tự nhập
    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_invoice_line_sync'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_invoice_line_sync=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        for line in after:
            if (
                    line.display_type == 'product'
                    and (not changed('amount_currency') or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(line.price_subtotal)
                if line.amount_currency != amount_currency or line not in before:
                    line.amount_currency = amount_currency
                if line.currency_id == line.company_id.currency_id:
                    line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                    (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                    and (not changed('balance') or (line not in before and not line.balance))
            ):
                balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                line.balance = balance
                # sửa ở đây
                if line.move_id.currency_id != line.company_id.currency_id and line.move_id.exchange_rate > 0:
                    rates = line.move_id.currency_id._get_rates(line.company_id, line.date)
                    line.balance = balance * rates.get(line.move_id.currency_id.id) * line.move_id.exchange_rate

        # Since this method is called during the sync, inside of `create`/`write`, these fields
        # already have been computed and marked as so. But this method should re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])

    @api.depends('tax_ids', 'price_subtotal')
    def _compute_tax_amount(self):
        for rec in self:
            if rec.tax_ids and rec.price_subtotal:
                for item in rec.tax_ids:
                    rec.tax_amount = (item.amount / 100) * rec.price_subtotal

    @api.onchange("discount")
    def _onchange_discount_value(self):
        if self.discount:
            self.discount_value = self.price_unit * self.quantity * (self.discount / 100)
            self.readonly_discount_value = True
        elif self.discount == 0:
            self.discount_value = 0
            self.readonly_discount_value = False
        else:
            self.readonly_discount_value = False

    @api.onchange("discount_value")
    def _onchange_discount(self):
        if self.discount_value and self.price_unit > 0 and self.quantity > 0:
            self.discount = (self.discount_value / (self.price_unit * self.quantity))
            self.readonly_discount = True
        elif self.discount_value == 0:
            self.discount = 0
            self.readonly_discount = False
        else:
            self.readonly_discount = False

    is_check_promotions = fields.Boolean('Dùng để readonly line nếu self.promotions = True')

    @api.onchange('promotions')
    def onchange_vendor_prices(self):
        if self.promotions and (self.partner_id.is_passersby or not self.partner_id.is_passersby):
            self.vendor_price = self.price_unit = self.discount = self.discount_value = self.tax_amount = self.total_vnd_amount = False
            self.tax_ids = False
            self.is_check_promotions = True
        else:
            self.is_check_promotions = False

class RespartnerVendor(models.Model):
    _name = "vendor.back"
    _description = 'Vendor back'

    _sql_constraints = [
        (
            "discount_limit",
            "CHECK (tax_percent_back <= 100.0)",
            "Discount Pervent must be lower than 100%.",
        )
    ]

    vendor_back_id = fields.Many2one('account.move', ondelete='cascade')
    vendor = fields.Char(string='Tên nhà cung cấp')
    code_tax = fields.Char(string='Mã số thuế')
    street_ven = fields.Char(string='Địa chỉ')
    company_id = fields.Many2one('res.company', string='Công ty')
    invoice_reference = fields.Char(string='Số hóa đơn')
    invoice_description = fields.Many2one('product.product', string="Diễn giải hóa đơn")
    price_subtotal_back = fields.Float(string='Thành tiền')
    tax_back = fields.Float(string='Tiền thuế', compute='compute_tax')
    totals_back = fields.Float(string='Tổng tiền sau thuế', compute='compute_totals_back')
    _x_invoice_date = fields.Date(string='Ngày hóa đơn')
    tax_percent = fields.Many2one('account.tax', string='% Thuế')
    date_due = fields.Date(string='Hạn xử lý')
    currency_id = fields.Many2one('res.currency', related='vendor_back_id.currency_id', string='Currency')

    def unlink(self):
        for rec in self:
            if rec.vendor_back_id.select_type_inv != 'expense':
                continue
            invoice_line = rec.vendor_back_id.invoice_line_ids.filtered(
                lambda x: x.product_id == rec.invoice_description)
            if invoice_line:
                invoice_line.unlink()
        return super().unlink()

    @api.depends('tax_percent', 'price_subtotal_back')
    def compute_tax(self):
        for rec in self:
            rec.tax_back = rec.price_subtotal_back * rec.tax_percent.amount * 0.01

    @api.constrains('price_subtotal_back')
    def constrains_check_less_than(self):
        for rec in self:
            if rec.price_subtotal_back < 0:
                raise ValidationError(_('Bạn không được nhập thành tiền nhỏ hơn 0 !!'))

    @api.onchange("tax_percent_back")
    def _onchange_tax_percent_back(self):
        if self.tax_percent_back:
            self.tax_back = self.tax_percent_back * self.price_subtotal_back * 0.01
        if self.tax_percent_back == 0:
            self.tax_back = 0

    @api.depends('tax_back', 'price_subtotal_back')
    def compute_totals_back(self):
        for rec in self:
            rec.totals_back = rec.price_subtotal_back + rec.tax_back


class InvoiceCostLine(models.Model):
    _name = "invoice.cost.line"
    _description = 'Invoice Cost Line'

    product_id = fields.Many2one('product.product', string='Sản phẩm', domain=[('detailed_type', '=', 'service')])
    name = fields.Char(string='Mô tả', related='product_id.name')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=1)
    exchange_rate = fields.Float(string='Tỷ giá', default=1)
    foreign_amount = fields.Float(string='Tổng tiền ngoại tệ')
    vnd_amount = fields.Float(string='Tổng tiền VNĐ', compute='compute_vnd_amount', inverse="_inverse_cost", store=1, readonly=False)
    is_check_pre_tax_costs = fields.Boolean('Chi phí trước thuế', default=False)
    cost_line_origin = fields.Many2one('purchase.order.cost.line', string='Chi phí gốc')
    invoice_cost_id = fields.Many2one('account.move', string='Invoice Cost Line', ondelete='cascade')
    company_currency = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)

    @api.model
    def _inverse_cost(self):
        for rec in self:
            if rec.invoice_cost_id.select_type_inv != 'normal' or not rec.cost_line_origin or (rec.cost_line_origin.vnd_amount != 0 and rec.cost_line_origin.vnd_amount <= rec.cost_line_origin.actual_cost):
                return
            rec.cost_line_origin.write({'actual_cost': rec.cost_line_origin.actual_cost + rec.vnd_amount})

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            self.exchange_rate = self.currency_id.inverse_rate

    @api.depends('exchange_rate', 'foreign_amount')
    def compute_vnd_amount(self):
        for rec in self:
            rec.vnd_amount = rec.exchange_rate * rec.foreign_amount
