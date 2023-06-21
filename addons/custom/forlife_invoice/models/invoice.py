from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time
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
        ('product', 'Goods'),
        ('asset', 'Asset'),
        ('service', 'Service'),
    ], string='PO Type', default='product')
    type_inv = fields.Selection([('tax', 'Nhập khẩu'), ('cost', 'Nội địa')], string='Loại hóa đơn')
    number_bills = fields.Char(string='Number bills', copy=False)
    reference = fields.Char(string='Source Material')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 8), default=1)
    accounting_date = fields.Datetime(string='Accounting Date')
    payment_status = fields.Char(string='Payment onchange_purchase_typestatus')
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    is_check_cost_view = fields.Boolean(default=False, string='Hóa đơn chi phí')
    is_check_cost_out_source = fields.Boolean(default=False, string='Hóa đơn chi phí thuê ngoài')
    is_check_invoice_tnk = fields.Boolean(default=False)

    @api.onchange('is_check_cost_view')
    def _onchange_is_check_cost_view(self):
        if self.is_check_cost_view and self.is_check_cost_out_source:
            self.is_check_cost_out_source = False


    @api.onchange('is_check_cost_out_source')
    def _onchange_is_check_cost_out_source(self):
        if self.is_check_cost_view and self.is_check_cost_out_source:
            self.is_check_cost_view = False

    transportation_total = fields.Float(string='Tổng chi phí vận chuyển')
    loading_total = fields.Float(string='Tổng chi phí bốc dỡ')
    custom_total = fields.Float(string='Tổng chi phí thông quan')
    payment_term_invoice = fields.Many2one('account.payment.term', string='Chính sách thanh toán')

    trade_discount = fields.Integer(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Integer(string='Tổng chiết khấu thương mại')

    # field domain cho 2 field đơn mua hàng và phiếu nhập kho
    purchase_order_product_id = fields.Many2many('purchase.order', string='Purchase Order')
    receiving_warehouse_id = fields.Many2many('stock.picking')

    # field chi phí và thuế nhập khẩu
    exchange_rate_line = fields.One2many('invoice.exchange.rate', 'invoice_rate_id',
                                         string='Invoice Exchange Rate',
                                         compute='_compute_exchange_rate_line_and_cost_line',
                                         store=1)
    cost_line = fields.One2many('invoice.cost.line', 'invoice_cost_id',
                                string='Invoice Cost Line',
                                compute='_compute_exchange_rate_line_and_cost_line',
                                store=1)
    invoice_synthetic_ids = fields.One2many('forlife.invoice.synthetic', 'synthetic_id',
                                            compute='_compute_exchange_rate_line_and_cost_line',
                                            store=1)
    vendor_back_ids = fields.One2many('vendor.back', 'vendor_back_id',
                                      string='Vendor Back',
                                      compute='_compute_is_check_vendor_page',
                                      store=1,
                                      readonly=False)

    # Field check k cho tạo addline khi hóa đơn đã có PO
    is_check = fields.Boolean()
    is_check_quantity_readonly = fields.Boolean()

    # Field check page ncc vãng lại
    is_check_vendor_page = fields.Boolean(compute='_compute_is_check_vendor_page',
                                          store=1)

    # tab e-invoice-bkav
    e_invoice_ids = fields.One2many('e.invoice', 'e_invoice_id', string='e Invoice')

    # lấy id để search ghi lại ref cho bút toán phát sinh
    e_in_check = fields.Char('')

    x_asset_fin = fields.Selection([
        ('TC', 'TC'),
        ('QT', 'QT'),
    ], string='Phân loại tài chính')

    x_root = fields.Selection([
        ('Intel ', 'Intel '),
        ('Winning', 'Winning'),
    ], string='Phân loại nguồn')

    @api.onchange('exists_bkav')
    def onchange_exitsts_bakv_e_invoice(self):
        for rec in self:
            if rec.exists_bkav:
                data_e_invoice = self.env['e.invoice'].search(
                    [('e_invoice_id', '=', rec.id), ('number_e_invoice', '=', rec.invoice_no),
                     ('date_start_e_invoice', '=', rec.create_date), ('state_e_invoice', '=', rec.invoice_state_e)], limit=1)
                if not data_e_invoice:
                    self.env['e.invoice'].create({
                        'number_e_invoice': rec.invoice_no,
                        'date_start_e_invoice': rec.create_date,
                        'state_e_invoice': rec.invoice_state_e,
                        'e_invoice_id': rec.id,
                    })
                rec.e_invoice_ids = [(6, 0, data_e_invoice.ids)]

    @api.onchange('partner_id', 'currency_id')
    def onchange_partner_id_warning(self):
        if self.partner_id and self.invoice_line_ids and self.currency_id:
            for item in self.invoice_line_ids:
                if item.product_id:
                    item.product_uom = item.product_id.uom_id.id
                    date_item = datetime.now().date()
                    supplier_info = self.env['product.supplierinfo'].search(
                        [('product_id', '=', item.product_id.id), ('partner_id', '=', self.partner_id.id),
                         ('date_start', '<', date_item),
                         ('date_end', '>', date_item),
                         ('currency_id', '=', self.currency_id.id)
                         ])
                    if supplier_info:
                        item.purchase_uom = supplier_info[-1].product_uom
                        data = self.env['product.supplierinfo'].search([
                            ('product_tmpl_id', '=', item.product_id.product_tmpl_id.id),
                            ('partner_id', '=', self.partner_id.id),
                            ('product_uom', '=', item.purchase_uom.id),
                            ('amount_conversion', '=', item.exchange_quantity)
                        ], limit=1)
                        item.vendor_price = data.price if data else False
                        item.price_unit = item.vendor_price / item.exchange_quantity if item.exchange_quantity else False

    @api.onchange('partner_id', 'partner_id.group_id')
    def onchange_partner_id(self):
        if self.partner_id.group_id:
            if self.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_2').id:
                self.type_inv = 'cost'
            if self.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id:
                self.type_inv = 'tax'

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            if self.type_inv != 'cost':
                self.exchange_rate = self.currency_id.inverse_rate
            else:
                self.exchange_rate = 1

    domain_receiving_warehouse_id = fields.Char(compute='_compute_domain_receiving_warehouse_id', store=1)

    @api.depends('purchase_order_product_id')
    def _compute_domain_receiving_warehouse_id(self):
        receiving = {}
        for p in self.env['stock.picking'].search([
            ('origin', '=', self.mapped('purchase_order_product_id.name')),
            ('location_dest_id', '=', self.mapped('purchase_order_product_id.location_id.id')),
            ('state', '=', 'done'), ('picking_type_id.code', '=', 'incoming')
        ]):
            receiving_k = '{}{}'.format(p.origin, p.location_dest_id.id)
            if receiving_k in receiving:
                receiving[receiving_k] += p._ids
                continue
            receiving[receiving_k] = p._ids
        for rec in self:
            picking_ids = ()
            for purchase_order_product_id in rec.purchase_order_product_id:
                k = '{}{}'.format(purchase_order_product_id.name, purchase_order_product_id.location_id.id)
                if k in receiving:
                    picking_ids += receiving[k]
            rec.domain_receiving_warehouse_id = json.dumps([('id', 'in', picking_ids)])

    @api.onchange('purchase_order_product_id')
    def onchange_purchase_order_product_id(self):
        location_ids = []
        self.receiving_warehouse_id = [(5, 0)]
        if self.purchase_order_product_id:
            receiving_warehouse = []
            product_cost = self.env['purchase.order'].search([('id', 'in', self.purchase_order_product_id.ids)])
            for po in product_cost:
                location_ids.append(po.location_id)
                receiving_warehouse_id = self.env['stock.picking'].search(
                    [('origin', '=', po.name), ('location_dest_id', '=', po.location_id.id),
                     ('state', '=', 'done')])
                if receiving_warehouse_id.picking_type_id.code == 'incoming':
                    for item in receiving_warehouse_id:
                        receiving_warehouse.append(item.id)
                        self.receiving_warehouse_id = [(6, 0, receiving_warehouse)]

    @api.onchange('receiving_warehouse_id', 'partner_id', 'is_check_cost_view', 'is_check_cost_out_source')
    def onchange_is_check_cost_view_or_is_check_cost_out_source_or_purchase_order_product_id_or_partner_id(self):
        for rec in self:
            list_money = []
            before_tax = []
            rec.invoice_line_ids = [(5, 0)]
            if rec.partner_id:
                invoice_line_ids = rec.invoice_line_ids.filtered(lambda line: line.product_id)  # Lọc các dòng có product_id
                if rec.receiving_warehouse_id:
                    product_cost = self.env['purchase.order'].search([('id', 'in', rec.purchase_order_product_id.ids)])
                    if rec.is_check_cost_view:
                        rec.purchase_type = 'service'
                        for po_l, pnk_l in zip(product_cost.order_line, rec.receiving_warehouse_id.move_ids_without_package):
                            if pnk_l.picking_id.state == 'done':
                                if pnk_l.quantity_done * po_l.price_unit != 0:
                                    list_money.append((pnk_l.quantity_done * po_l.price_unit - po_l.discount) * po_l.order_id.exchange_rate)
                        total_money = sum(list_money)
                        for total in list_money:
                            for co in product_cost.cost_line:
                                before_tax.append(total / total_money * co.vnd_amount)
                        sum_before_tax = sum(before_tax)
                        for cost in product_cost.cost_line:
                            for item, exchange, total, pk_l in zip(product_cost.order_line,product_cost.exchange_rate_line, list_money,rec.receiving_warehouse_id.move_ids_without_package):
                                if not cost.product_id.categ_id and cost.product_id.categ_id.with_company(
                                        rec.company_id).property_stock_account_input_categ_id:
                                    raise ValidationError(
                                        _("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % cost.product_id.name)
                                else:
                                    if rec.type_inv == 'tax':
                                        if cost.is_check_pre_tax_costs:
                                            cost_total = ((total / total_money) * (cost.vnd_amount * pk_l.quantity_done / item.product_qty))
                                        else:
                                            cost_total = ((total + (total / total_money * cost.vnd_amount) + exchange.tax_amount + exchange.special_consumption_tax_amount) / (total_money + sum_before_tax)) * (cost.vnd_amount * pk_l.quantity_done / item.product_qty)
                                    else:
                                        if cost.is_check_pre_tax_costs:
                                            cost_total = ((total / total_money) * (cost.vnd_amount * pk_l.quantity_done / item.product_qty))
                                        else:
                                            cost_total = ((total / total_money) * (cost.vnd_amount * pk_l.quantity_done / item.product_qty))
                                existing_line = invoice_line_ids.filtered(
                                    lambda line: line.product_id.id == cost.product_id.id)
                                if not existing_line:
                                    invoice_line_ids += self.env['account.move.line'].new({
                                        'product_id': cost.product_id.id,
                                        'description': cost.name,
                                        'price_unit': cost_total,
                                        'cost_id': cost.id,
                                    })
                                else:
                                    existing_line.price_unit += cost_total
                            rec.invoice_line_ids = invoice_line_ids
                    elif rec.is_check_cost_out_source:
                        rec.purchase_type = 'service'
                        for out_source, pnk_l in zip(product_cost.order_line_production_order,rec.receiving_warehouse_id.move_ids_without_package):
                            for out_source_line in out_source.purchase_order_line_material_line_ids:
                                if out_source_line.product_id.product_tmpl_id.x_type_cost_product == 'labor_costs':
                                    if not out_source_line.product_id.categ_id and out_source_line.product_id.categ_id.with_company(
                                            rec.company_id).property_stock_account_input_categ_id:
                                        raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % out_source_line.product_id.name)
                                    else:
                                        existing_line = invoice_line_ids.filtered(
                                            lambda line: line.product_id.id == out_source_line.product_id.id)
                                        if not existing_line:
                                            invoice_line_ids += self.env['account.move.line'].new({
                                                'product_id': out_source_line.product_id.id,
                                                'description': out_source_line.name,
                                                'price_unit': out_source_line.price_unit * (pnk_l.quantity_done / out_source.product_qty),
                                                'cost_id': out_source_line.id,
                                            })
                                        else:
                                            existing_line.price_unit += out_source_line.price_unit * (pnk_l.quantity_done / out_source.product_qty)
                                rec.invoice_line_ids = invoice_line_ids
                    else:
                        rec.purchase_type = 'product'
                        for product in product_cost.order_line:
                            for pnk in rec.receiving_warehouse_id.move_line_ids_without_package:
                                if not product.product_id.categ_id and not product.product_id.categ_id.with_company(
                                        rec.company_id).property_stock_account_input_categ_id:
                                    raise ValidationError(
                                        _("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % product.product_id.name)
                                else:
                                    if str(product.id) == str(pnk.po_id):
                                        invoice_line_ids += self.env['account.move.line'].new({
                                            'product_id': product.product_id.id,
                                            'description': product.name,
                                            'request_code': product.request_purchases,
                                            'promotions': product.free_good,
                                            'quantity_purchased': pnk.quantity_purchase_done,
                                            'product_uom_id': product.purchase_uom.id,
                                            'exchange_quantity': pnk.quantity_change,
                                            'quantity': pnk.qty_done,
                                            'vendor_price': product.vendor_price,
                                            'price_unit': product.price_unit,
                                            'warehouse': product.location_id.id,
                                            'tax_ids': product.taxes_id.ids,
                                            'tax_amount': product.price_tax * pnk.qty_done / product.product_qty,
                                            'price_subtotal': product.price_subtotal,
                                            'discount_percent': product.discount * pnk.qty_done / product.product_qty,
                                            'discount': product.discount_percent * pnk.qty_done / product.product_qty,
                                            'event_id': product.free_good,
                                            'work_order': product.production_id.id,
                                            'account_analytic_id': product.account_analytic_id.id,
                                        })
                                rec.invoice_line_ids = invoice_line_ids
                else:
                    rec.receiving_warehouse_id = False
                    if rec.is_check_cost_view or rec.is_check_cost_out_source:
                        rec.purchase_type = 'service'
                    else:
                        rec.purchase_type = 'product'

    @api.onchange('line_ids', 'is_check_cost_view')
    def onchange_invoice_compute_po(self):
        for rec in self:
            data_search_po = self.env['purchase.order'].search(
                [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved'),
                 ('inventory_status', '=', 'done'), ('is_inter_company', '=', False), ('name', '=', rec.reference)])
            rec.purchase_order_product_id = [(6, 0, data_search_po.ids)]

    @api.constrains('invoice_line_ids', 'invoice_line_ids.quantity')
    def constrains_quantity_line(self):
        for rec in self:
            if rec.invoice_line_ids and rec.receiving_warehouse_id:
                for line, nine in zip(rec.invoice_line_ids, rec.receiving_warehouse_id):
                    for item in nine.move_line_ids_without_package:
                        if line.ware_name == nine.name and (line.quantity <= 0 or item.qty_done <= 0):
                            raise UserError(_("Số lượng hoàn thành của phiếu nhập kho %s hoặc số lượng của hóa đơn %s đang nhỏ hơn hoặc bằng 0") % (nine.name, line.move_id.name))
                        if line.ware_name == nine.name and str(line.po_id) == str(item.po_id) and line.product_id.id == item.product_id.id:
                            if line.quantity > item.qty_done:
                                raise UserError(_("Không thể tạo hóa đơn với số lượng lớn hơn phiếu nhập kho %s liên quan ") % nine.name)

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for rec in self:
            if rec.is_check_cost_view or rec.is_check_cost_out_source:
                for line in rec.invoice_line_ids:
                    if line.product_id and line.display_type == 'product':
                        line.write({
                            'account_id': line.product_id.categ_id.with_company(
                                line.company_id).property_stock_account_input_categ_id.id,
                            'name': line.product_id.name
                        })
            ### ghi key search bút toán liên quan cho invocie:
            entry_relation_ship_id = self.search([('move_type', '=', 'entry'),
                                                  ('e_in_check', '=', str(rec.id)),
                                                  ])
            if not entry_relation_ship_id:
                continue
            else:
                for line in entry_relation_ship_id:
                    line.write({
                        'ref': f"{str(rec.name)} - {str(line.invoice_description)}",
                    })
        return res

    @api.depends('partner_id.is_passersby', 'partner_id')
    def _compute_is_check_vendor_page(self):
        for rec in self:
            if rec.partner_id:
                if rec.partner_id.is_passersby:
                    vendor_back = self.env['vendor.back'].search([('vendor', '=', rec.partner_id.name),
                                                                  ('vendor_back_id', '=', rec.id),
                                                                  ('company_id', '=', rec.company_id.id),
                                                                  ('code_tax', '=', rec.partner_id.vat),
                                                                  ('street_ven', '=', rec.partner_id.street),
                                                                  ], limit=1)
                    if not vendor_back:
                        self.env['vendor.back'].create({'vendor': rec.partner_id.name,
                                                        'vendor_back_id': rec.id,
                                                        'company_id': rec.company_id.id,
                                                        'code_tax': rec.partner_id.vat,
                                                        'street_ven': rec.partner_id.street,
                                                        })
                    else:
                        rec.vendor_back_ids = [(6, 0, vendor_back.id)]
                    rec.is_check_vendor_page = True
                else:
                    rec.is_check_vendor_page = False

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
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_total') * (self.trade_discount / 100)

    @api.depends('purchase_order_product_id', 'purchase_order_product_id.exchange_rate_line', 'invoice_line_ids')
    def _compute_exchange_rate_line_and_cost_line(self):
        for rec in self:
            rec.exchange_rate_line = [(5, 0)]
            rec.cost_line = [(5, 0)]
            rec.invoice_synthetic_ids = [(5, 0)]
            for po in rec.purchase_order_product_id:
                if rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id or rec.type_inv == 'tax':
                    for exchange, invoice in zip(po.exchange_rate_line, rec.invoice_line_ids):
                        exchange_rate = self.env['invoice.exchange.rate'].create({
                            'ex_po_id': invoice.id,
                            'invoice_rate_id': rec.id,
                            'product_id': exchange.product_id.id,
                            'name': exchange.name,
                            'vnd_amount': exchange.vnd_amount,
                            'qty_product': exchange.qty_product,
                            'import_tax': exchange.import_tax,
                            'tax_amount': exchange.tax_amount,
                            'special_consumption_tax': exchange.special_consumption_tax,
                            'special_consumption_tax_amount': exchange.special_consumption_tax_amount,
                            'vat_tax': exchange.vat_tax,
                            'vat_tax_amount': exchange.vat_tax_amount,
                            'total_tax_amount': exchange.total_tax_amount,
                        })
                        if exchange_rate:
                            exchange_rate.update({
                                'ex_po_id': invoice.id,
                                'vnd_amount': invoice.total_vnd_amount,
                                'qty_product': invoice.quantity,
                            })
                for line in po.cost_line:
                    cost_line = self.env['invoice.cost.line'].create({
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'currency_id': line.currency_id.id,
                        'exchange_rate': line.exchange_rate,
                        'foreign_amount': line.foreign_amount,
                        'vnd_amount': line.vnd_amount,
                        'is_check_pre_tax_costs': line.is_check_pre_tax_costs,
                        'invoice_cost_id': rec.id,
                    })
                    if cost_line:
                        cost_line.update({
                            'currency_id': line.currency_id.id,
                            'exchange_rate': line.exchange_rate,
                            'foreign_amount': line.foreign_amount,
                            'vnd_amount': line.vnd_amount,
                            'is_check_pre_tax_costs': line.is_check_pre_tax_costs,
                        })
                for line, invoice in zip(po.purchase_synthetic_ids, rec.invoice_line_ids):
                    synthetic_line = self.env['forlife.invoice.synthetic'].create({
                        'syn_po_id': invoice.id,
                        'product_id': line.product_id.id,
                        'description': line.description,
                        'price_unit': line.price_unit,
                        'quantity': line.quantity,
                        'price_subtotal': invoice.total_vnd_amount,
                        'before_tax': line.before_tax,
                        'discount': line.discount,
                        'synthetic_id': rec.id,
                    })
                    if synthetic_line:
                        synthetic_line.update({
                            'quantity': invoice.quantity if invoice.quantity else 0,
                            'discount': invoice.discount_percent if invoice.discount_percent else 0,
                            'price_unit': invoice.price_unit if invoice.price_unit else 0,
                            'price_subtotal': invoice.total_vnd_amount,
                        })

    def create_invoice_tnk_db(self):
        for rec in self:
            account_db = []
            account_tnk = []
            if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id \
                    or not self.env.ref('forlife_purchase.product_import_tax_default').with_company(rec.company_id).property_account_expense_id:
                raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế nhập khẩu hoặc tài khoản chi phí kế toán của sản phẩm có tên là 'Thuế nhập khẩu'")
            if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id \
                    or not self.env.ref('forlife_purchase.product_excise_tax_default').with_company(rec.company_id).property_account_expense_id:
                raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế tiêu thụ đặc biệt hoặc tài khoản chi phí kế toán của sản phẩm có tên là 'Thuế tiêu thụ đặc biệt'")
            for item in rec.exchange_rate_line:
                account_credit_tnk = (0, 0, {
                    'sequence': 99991,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').with_company(
                        rec.company_id).property_account_expense_id.id,
                    'name': self.env.ref('forlife_purchase.product_import_tax_default').with_company(
                        rec.company_id).property_account_expense_id.name,
                    'debit': 0,
                    'credit': item.tax_amount * self.exchange_rate,
                })
                account_debit_tnk = (0, 0, {
                    'sequence': 9,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(
                        rec.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.tax_amount * self.exchange_rate,
                    'credit': 0,
                })
                lines_tnk = [account_debit_tnk, account_credit_tnk]
                account_tnk.extend(lines_tnk)
                account_credit_db = (0, 0, {
                    'sequence': 99991,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        rec.company_id).property_account_expense_id.id,
                    'name': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        rec.company_id).property_account_expense_id.name,
                    'debit': 0,
                    'credit': item.special_consumption_tax_amount * self.exchange_rate,
                })
                account_debit_db = (0, 0, {
                    'sequence': 9,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.special_consumption_tax_amount * self.exchange_rate,
                    'credit': 0,
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
                            'name': db[2]['name'],
                            'debit': db[2]['debit'],
                            'credit': db[2]['credit'],
                        }
                # Chuyển đổi từ điển thành danh sách bản ghi
            merged_records_list_tnk = [(0, 0, record) for record in merged_records_tnk.values()]
            merged_records_list_db = [(0, 0, record) for record in merged_records_db.values()]

            invoice_db = self.create({
                'e_in_check': self.id,
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': f"Thuế tiêu thụ đặc biệt",
                'line_ids': merged_records_list_db,
                'move_type': 'entry',
            })
            invoice_db.action_post()
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
        if not self.env.ref('forlife_purchase.product_vat_tax').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản chi phí kế toán thuế VAT (Nhập khẩu), trong sản phẩm có tên là Thuế VAT (Nhập khẩu) ở tab kế toán")
        if not self.env.ref('forlife_purchase.product_vat_tax').categ_id.with_company(self.company_id).property_stock_account_input_categ_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục sản phẩm có tên là Thuế VAT (Nhập khẩu)")
        for line in self.exchange_rate_line:
            account_credit_vat = (0, 0, {
                'sequence': 9,
                'account_id': self.env.ref('forlife_purchase.product_vat_tax').with_company(
                    self.company_id).property_account_expense_id.id,
                'name': 'thuế giá trị gia tăng nhập khẩu (VAT)',
                'debit': 0,
                'credit': line.vat_tax_amount * self.exchange_rate,
            })
            account_debit_vat = (0, 0, {
                'sequence': 99991,
                'account_id': self.env.ref('forlife_purchase.product_vat_tax').categ_id.with_company(
                    self.company_id).property_stock_account_input_categ_id.id,
                'name': line.name,
                'debit': line.vat_tax_amount * self.exchange_rate,
                'credit': 0,
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
        account_ck = []
        if not self.env.ref('forlife_purchase.product_discount_tax').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản chi phí ở tab kế toán trong danh sản phẩm có tên là Chiết khấu tổng đơn!!")
        if not self.partner_id.property_account_payable_id:
            raise ValidationError(_("Bạn chưa cấu hình tài khoản phải trả ở tab kế toán trong nhà cung cấp %s") %self.partner_id.name)
        account_331 = (0, 0, {
            'account_id': self.partner_id.property_account_payable_id.id,
            'name': self.partner_id.property_account_payable_id.name,
            'debit': self.total_trade_discount * self.exchange_rate,
            'credit': 0,
        })
        account_771 = (0, 0, {
            'account_id': self.env.ref('forlife_purchase.product_discount_tax').with_company(
                self.company_id).property_account_expense_id.id,
            'name': self.env.ref('forlife_purchase.product_discount_tax').with_company(
                self.company_id).property_account_expense_id.name,
            'debit': 0,
            'credit': self.total_trade_discount * self.exchange_rate,
        })
        lines_ck = [account_331, account_771]
        account_ck.extend(lines_ck)

        invoice_ck = self.env['account.move'].create({
            'e_in_check': self.id,
            'partner_id': self.partner_id.id,
            'ref': f"{self.name} Chiết khấu tổng đơn",
            'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') else False,
            'invoice_date': self.invoice_date,
            'invoice_description': f"Hóa đơn chiết khấu tổng đơn",
            'invoice_line_ids': account_ck,
            'move_type': 'entry',
        })
        invoice_ck.action_post()

    def action_post(self):
        for rec in self:
            if (rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id or rec.type_inv == 'tax') and rec.move_type != 'out_invoice':
                if rec.exchange_rate_line:
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
    ware_name = fields.Char('')
    type = fields.Selection(related="product_id.product_type", string='Loại mua hàng')
    work_order = fields.Many2one('forlife.production', string='Work Order')
    warehouse = fields.Many2one('stock.location', string='Whs')
    discount_percent = fields.Float(string='Chiết khấu', digits='Discount', default=0.0)
    tax_amount = fields.Monetary(string='Thuế', compute='_compute_tax_amount', store=1)

    # fields common !!
    production_order = fields.Many2one('forlife.production', string='Production order')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    occasion_code_id = fields.Many2one('occasion.code', string="Mã vụ việc")
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")

    # goods invoice!!
    promotions = fields.Boolean(string='Promotions', default=False)
    quantity_purchased = fields.Integer(string='Quantity Purchased', default=1)
    exchange_quantity = fields.Float(string='Exchange Quantity')
    request_code = fields.Char('Mã phiếu yêu cầu')
    vendor_price = fields.Float(string='Giá nhà cung cấp', compute='compute_vendor_price_ncc', store=1)
    total_vnd_amount = fields.Float('Tổng tiền VNĐ', compute='_compute_total_vnd_amount', store=1)

    @api.depends('exchange_quantity', 'quantity', 'product_id', 'purchase_uom',
                 'move_id.partner_id', 'move_id.partner_id.is_passersby', 'move_id', 'move_id.currency_id')
    def compute_vendor_price_ncc(self):
        today = datetime.now().date()
        for rec in self:
            if not (rec.product_id and rec.move_id.partner_id and rec.purchase_uom and rec.move_id.currency_id):
                rec.is_red_color = False
                continue
            data = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id),
                ('partner_id', '=', rec.move_id.partner_id.id),
                ('currency_id', '=', rec.move_id.currency_id.id),
                ('amount_conversion', '=', rec.exchange_quantity),
                ('date_start', '<=', today),
                ('date_end', '>=', today)
            ])
            rec.is_red_color = True if rec.exchange_quantity not in data.mapped(
                'amount_conversion') else False
            if rec.product_id and rec.move_id.partner_id and rec.purchase_uom and rec.move_id.currency_id and not rec.is_red_color and not rec.move_id.partner_id.is_passersby:
                for line in data:
                    if line.product_uom.id == rec.purchase_uom.id:
                        rec.vendor_price = line.price if line else False
                        rec.exchange_quantity = line.amount_conversion
                    else:
                        if rec.quantity:
                            if rec.quantity > max(data.mapped('min_qty')):
                                closest_quantity = max(data.mapped('min_qty'))
                                if closest_quantity == line.min_qty:
                                    rec.vendor_price = line.price
                                    rec.exchange_quantity = line.amount_conversion
                            else:
                                closest_quantity = min(data.mapped('min_qty'), key=lambda x: abs(x - rec.quantity))
                                if closest_quantity == line.min_qty:
                                    rec.vendor_price = line.price
                                    rec.exchange_quantity = line.amount_conversion

    # asset invoice!!
    asset_code = fields.Char('Mã tài sản cố định')
    asset_name = fields.Char('Mô tả tài sản cố định')
    code_tax = fields.Char(string='Mã số thuế')
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")
    purchase_uom = fields.Many2one('uom.uom', string='Purchase UOM')

    # field check exchange_quantity khi ncc vãng lại:
    is_check_exchange_quantity = fields.Boolean(default=False)

    # field check vendor_price khi ncc vãng lại:
    is_passersby = fields.Boolean(related='move_id.is_passersby')
    is_red_color = fields.Boolean(compute='compute_vendor_price_ncc')

    @api.depends('display_type', 'company_id')
    def _compute_account_id(self):
        res = super()._compute_account_id()
        for line in self:
            if line.product_id and line.move_id.purchase_order_product_id and line.move_id.purchase_order_product_id[0].is_inter_company == False:
                line.account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                line.name = line.product_id.name
        return res

    @api.onchange('vendor_price')
    def onchange_vendor_price(self):
        self.price_unit = self.vendor_price

    @api.onchange('quantity_purchased', 'exchange_quantity')
    def onchange_quantity_purchased(self):
        self.quantity = self.quantity_purchased * self.exchange_quantity

    @api.onchange('quantity', 'exchange_quantity')
    def onchange_quantity(self):
        self.quantity_purchased = self.quantity / self.exchange_quantity

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

    @api.depends('tax_ids', 'price_subtotal')
    def _compute_tax_amount(self):
        for rec in self:
            if rec.tax_ids and rec.price_subtotal:
                for item in rec.tax_ids:
                    rec.tax_amount = (item.amount / 100) * rec.price_subtotal

    @api.depends('price_subtotal', 'move_id.exchange_rate', 'move_id')
    def _compute_total_vnd_amount(self):
        for rec in self:
            if rec.price_subtotal and rec.move_id.exchange_rate:
                rec.total_vnd_amount = rec.price_subtotal * rec.move_id.exchange_rate

    @api.onchange("discount")
    def _onchange_discount_percent(self):
        if self.discount:
            self.discount_percent = self.discount * self.price_unit * self.quantity * 0.01
        elif self.discount == 0:
            self.discount_percent = 0

    @api.onchange("discount_percent")
    def _onchange_discount(self):
        if self.discount_percent and self.price_unit > 0 and self.quantity > 0:
            self.discount = self.discount_percent / (self.price_unit * self.quantity * 0.01)
        elif self.discount_percent == 0:
            self.discount = 0

    is_check_promotions = fields.Boolean('Dùng để readonly line nếu self.promotions = True')

    @api.onchange('promotions')
    def onchange_vendor_prices(self):
        if self.promotions and (self.partner_id.is_passersby or not self.partner_id.is_passersby):
            self.vendor_price = self.price_unit = self.discount = self.discount_percent = self.tax_amount = self.total_vnd_amount = False
            self.tax_ids = False
            self.is_check_promotions = True
        else:
            self.is_check_promotions = False

class RespartnerVendor(models.Model):
    _name = "vendor.back"

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
    invoice_description = fields.Char(string="Diễn giải hóa đơn")
    price_subtotal_back = fields.Float(string='Thành tiền')
    tax_back = fields.Float(string='Tiền thuế')
    tax_percent_back = fields.Float(string='% Thuế')
    totals_back = fields.Float(string='Tổng tiền sau thuế', compute='compute_totals_back', store=1)
    _x_invoice_date = fields.Date(string='Ngày hóa đơn')
    tax_percent = fields.Many2one('account.tax', string='% Thuế')

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

    @api.constrains('totals_back', 'vendor_back_id.total_tax')
    def constrains_vendor_back_by_invocie(self):
        for rec in self:
            sum_subtotal = sum(rec.vendor_back_id.invoice_line_ids.mapped('price_subtotal'))
            sum_tax = sum(rec.vendor_back_id.invoice_line_ids.mapped('tax_amount'))
            if rec.totals_back:
                if sum_subtotal + sum_tax == rec.totals_back:
                    pass
                else:
                    raise ValidationError(_('Bạn không thể lưu hóa đơn khi thành tiền sau thuế của ncc vãng lai không bằng bên tồng tiền sau thuế chi tiết hóa đơn'))


class InvoiceExchangeRate(models.Model):
    _name = "invoice.exchange.rate"
    _description = 'Invoice Exchange Rate'

    ex_po_id = fields.Char('')

    name = fields.Char(string='Tên sản phẩm')
    product_id = fields.Many2one('product.product', string='Mã sản phẩm')

    usd_amount = fields.Float(string='Thành tiền (USD)')  # đây chính là cột Thành tiền bên tab Sản phầm, a Trung đã viết trước
    vnd_amount = fields.Float(string='Thành tiền (VND)', compute='compute_vnd_amount', store=1)

    import_tax = fields.Float(string='% Thuế nhập khẩu')
    tax_amount = fields.Float(string='Tiền thuế nhập khẩu', compute='_compute_tax_amount', store=1, inverse='_inverse_tax_amount')

    special_consumption_tax = fields.Float(string='% %Thuế tiêu thụ đặc biệt')
    special_consumption_tax_amount = fields.Float(string='Thuế tiêu thụ đặc biệt',
                                                  compute='_compute_special_consumption_tax_amount', store=1)

    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='Thuế GTGT', compute='_compute_vat_tax_amount', store=1)

    # total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Tổng tiền thuế', compute='compute_tax_amount', store=1)
    invoice_rate_id = fields.Many2one('account.move', string='Invoice Exchange Rate')
    qty_product = fields.Float(copy=True, string="Số lượng đặt mua")

    def _inverse_tax_amount(self):
        pass

    @api.constrains('import_tax', 'special_consumption_tax', 'vat_tax')
    def constrains_per(self):
        for item in self:
            if item.import_tax < 0:
                raise ValidationError('% thuế nhập khẩu phải >= 0 !')
            if item.special_consumption_tax < 0:
                raise ValidationError('% thuế tiêu thụ đặc biệt phải >= 0 !')
            if item.import_tax < 0:
                raise ValidationError('% thuế GTGT >= 0 !')

    @api.depends('purchase_order_id.order_line.total_vnd_amount')
    def _compute_vnd_amount(self):
        for rec in self:
            for item in rec.invoice_rate_id.invoice_line_ids:
                if item.total_vnd_amount and rec.ex_po_id == str(item.id):
                    rec.vnd_amount = item.total_vnd_amount

    @api.depends('vnd_amount', 'import_tax')
    def _compute_tax_amount(self):
        for rec in self:
            rec.tax_amount = rec.vnd_amount * rec.import_tax / 100

    @api.depends('tax_amount', 'special_consumption_tax')
    def _compute_special_consumption_tax_amount(self):
        for rec in self:
            rec.special_consumption_tax_amount = (rec.vnd_amount + rec.tax_amount) * rec.special_consumption_tax / 100

    @api.depends('special_consumption_tax_amount', 'vat_tax')
    def _compute_vat_tax_amount(self):
        for rec in self:
            rec.vat_tax_amount = (rec.vnd_amount + rec.tax_amount + rec.special_consumption_tax_amount) * rec.vat_tax / 100

    @api.depends('vat_tax_amount')
    def compute_tax_amount(self):
        for rec in self:
            rec.total_tax_amount = rec.tax_amount + rec.special_consumption_tax_amount + rec.vat_tax_amount


class InvoiceCostLine(models.Model):
    _name = "invoice.cost.line"
    _description = 'Invoice Cost Line'

    product_id = fields.Many2one('product.product', string='Sản phẩm', domain=[('detailed_type', '=', 'service')])
    name = fields.Char(string='Mô tả', related='product_id.name')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=1)
    exchange_rate = fields.Float(string='Tỷ giá')
    foreign_amount = fields.Float(string='Tổng tiền ngoại tệ̣')
    vnd_amount = fields.Float(string='Tổng tiền VNĐ', compute='compute_vnd_amount', store=1, readonly=False)
    is_check_pre_tax_costs = fields.Boolean('Chi phí trước thuế', default=False)

    invoice_cost_id = fields.Many2one('account.move', string='Invoice Cost Line')

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            self.exchange_rate = self.currency_id.inverse_rate

    @api.depends('exchange_rate', 'foreign_amount')
    def compute_vnd_amount(self):
        for rec in self:
            rec.vnd_amount = rec.exchange_rate * rec.foreign_amount


class eInvoice(models.Model):
    _name = 'e.invoice'
    _description = 'e Invoice'

    e_invoice_id = fields.Many2one('account.move', string='e invoice')

    number_e_invoice = fields.Char('Số HĐĐT')
    date_start_e_invoice = fields.Char('Ngày phát hành HĐĐT')
    state_e_invoice = fields.Char('Trạng thái HĐĐT', related='e_invoice_id.invoice_state_e')


class SyntheticInvoice(models.Model):
    _name = 'forlife.invoice.synthetic'

    synthetic_id = fields.Many2one('account.move')
    syn_po_id = fields.Char('')

    description = fields.Char(string='Mã hàng')
    product_id = fields.Many2one('product.product', string='Tên hàng')
    product_uom = fields.Many2one(related='product_id.uom_id', string='ĐVT')
    price_unit = fields.Float(string='Đơn giá')
    quantity = fields.Float(string='Số lượng')
    price_subtotal = fields.Float(string='Thành tiền (VND)')
    discount = fields.Float(string='Chiết khấu')
    before_tax = fields.Float(string='Chi phí trước tính thuế', compute='_compute_is_check_pre_tax_costs', store=1)
    tnk_tax = fields.Float(string='Thuế nhập khẩu', compute='_compute_tnk_tax', store=1)
    db_tax = fields.Float(string='Thuế tiêu thụ đặc biệt', compute='_compute_db_tax', store=1)
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)', compute='_compute_after_tax', store=1)
    total_product = fields.Float(string='Tổng giá trị tiền hàng', compute='_compute_total_product', store=1)

    @api.depends('synthetic_id.cost_line.is_check_pre_tax_costs',
                 'synthetic_id.invoice_line_ids.total_vnd_amount',
                 'synthetic_id.exchange_rate_line')
    def _compute_is_check_pre_tax_costs(self):
        for rec in self:
            cost_line_true = rec.synthetic_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            for line, nine in zip(rec.synthetic_id.exchange_rate_line, rec.synthetic_id.invoice_line_ids):
                total_cost_true = 0
                if cost_line_true:
                    if nine.total_vnd_amount and rec.syn_po_id == str(nine.id):
                        rec.price_subtotal = nine.total_vnd_amount
                    for item in cost_line_true:
                        if item.vnd_amount and nine.total_vnd_amount > 0:
                            before_tax = nine.total_vnd_amount / sum(rec.synthetic_id.invoice_line_ids.mapped('total_vnd_amount')) * item.vnd_amount
                            total_cost_true += before_tax
                        if rec.product_id.id == line.product_id.id and rec.syn_po_id == line.ex_po_id:
                            rec.before_tax = total_cost_true
                else:
                    rec.before_tax = 0
                if rec.product_id.id == line.product_id.id and rec.syn_po_id == line.ex_po_id:
                    line.vnd_amount = nine.total_vnd_amount + rec.before_tax

    @api.depends('synthetic_id.exchange_rate_line.vnd_amount',
                 'synthetic_id.exchange_rate_line.tax_amount',
                 'synthetic_id.exchange_rate_line.special_consumption_tax_amount',
                 'synthetic_id.cost_line.is_check_pre_tax_costs', )
    def _compute_after_tax(self):
        for rec in self:
            cost_line_false = rec.synthetic_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            for line in rec.synthetic_id.exchange_rate_line:
                if cost_line_false:
                    total_cost = 0
                    sum_vnd_amount = sum(rec.synthetic_id.exchange_rate_line.mapped('vnd_amount'))
                    sum_tnk = sum(rec.synthetic_id.exchange_rate_line.mapped('tax_amount'))
                    sum_db = sum(rec.synthetic_id.exchange_rate_line.mapped('special_consumption_tax_amount'))
                    if rec.synthetic_id.type_inv == 'tax' and rec.syn_po_id == line.ex_po_id:
                        for item in cost_line_false:
                            if item.vnd_amount and sum_vnd_amount and sum_tnk and sum_db:
                                total_cost += (line.vnd_amount + line.tax_amount + line.special_consumption_tax_amount) / (sum_vnd_amount + sum_tnk + sum_db) * item.vnd_amount
                                if rec.product_id.id == line.product_id.id and rec.syn_po_id == line.ex_po_id:
                                    rec.after_tax = total_cost
                else:
                    rec.after_tax = 0

    @api.depends('price_subtotal', 'discount', 'before_tax', 'tnk_tax', 'db_tax', 'after_tax')
    def _compute_total_product(self):
        for record in self:
            record.total_product = record.price_subtotal + record.before_tax + record.tnk_tax + record.db_tax + record.after_tax

    @api.depends('synthetic_id.exchange_rate_line.tax_amount')
    def _compute_tnk_tax(self):
        for record in self:
            tnk_tax_total = 0.0
            for item in record.synthetic_id.exchange_rate_line:
                if record.product_id.id == item.product_id.id and record.syn_po_id == item.ex_po_id:
                    tnk_tax_total += item.tax_amount
            record.tnk_tax = tnk_tax_total

    @api.depends('synthetic_id.exchange_rate_line.special_consumption_tax_amount')
    def _compute_db_tax(self):
        for record in self:
            db_tax_total = 0.0
            for item in record.synthetic_id.exchange_rate_line:
                if record.product_id.id == item.product_id.id and record.syn_po_id == item.ex_po_id:
                    db_tax_total += item.special_consumption_tax_amount
            record.db_tax = db_tax_total
