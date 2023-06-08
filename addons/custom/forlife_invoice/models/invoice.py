from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
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
    receiving_warehouse_id = fields.Many2many('stock.picking', string='Receiving Warehouse')
    purchase_order_product_id = fields.Many2many('purchase.order', string='Purchase Order')
    partner_domain = fields.Char(compute='_compute_partner_domain', store=1)
    partner_domain_2 = fields.Char(compute='_compute_partner_domain_2', store=1)

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
    is_check = fields.Boolean(default=False)

    # Field check page ncc vãng lại
    is_check_vendor_page = fields.Boolean(default=False,
                                          compute='_compute_is_check_vendor_page',
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

    @api.depends('partner_id', 'partner_id.group_id')
    def _compute_partner_domain(self):
        self = self.sudo()
        for rec in self:
            if rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_2').id or rec.type_inv == 'cost':
                data_search = self.env['purchase.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved'),
                     ('inventory_status', '=', 'done'), ('type_po_cost', '=', 'cost'), ('is_inter_company', '=', False)])
                rec.partner_domain = json.dumps([('id', 'in', data_search.ids)])
            elif rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id or rec.type_inv == 'tax':
                data_search_2 = self.env['purchase.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved'),
                     ('inventory_status', '=', 'done'), ('type_po_cost', '=', 'tax'), ('is_inter_company', '=', False)])
                rec.partner_domain = json.dumps([('id', 'in', data_search_2.ids)])
            else:
                data_search_3 = self.env['purchase.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved'),
                     ('inventory_status', '=', 'done'), ('is_inter_company', '=', False)])
                rec.partner_domain = json.dumps([('id', 'in', data_search_3.ids)])

    @api.depends('purchase_order_product_id')
    def _compute_partner_domain_2(self):
        self = self.sudo()
        for rec in self:
            if rec.purchase_order_product_id:
                for po in rec.purchase_order_product_id:
                    receiving_warehouse_id = self.env['stock.picking'].search(
                        [('origin', '=', po.name), ('location_dest_id', '=', po.location_id.id),
                         ('state', '=', 'done')])
                rec.partner_domain_2 = json.dumps([('id', 'in', receiving_warehouse_id.ids)])
            else:
                receiving_warehouse_id = self.env['stock.picking'].search(
                    [('state', '=', 'done')])
                rec.partner_domain_2 = json.dumps([('id', 'in', receiving_warehouse_id.ids)])

    @api.onchange('purchase_order_product_id')
    def onchange_purchase_order_product_id(self):
        if self.purchase_order_product_id:
            receiving_warehouse = []
            product_cost = self.env['purchase.order'].search([('id', 'in', self.purchase_order_product_id.ids)])
            for po in product_cost:
                receiving_warehouse_id = self.env['stock.picking'].search(
                    [('origin', '=', po.name), ('location_dest_id', '=', po.location_id.id),
                     ('state', '=', 'done')])
                if receiving_warehouse_id.picking_type_id.code == 'incoming':
                    for item in receiving_warehouse_id:
                        receiving_warehouse.append(item.id)
                        self.receiving_warehouse_id = [(6, 0, receiving_warehouse)]

    @api.onchange('is_check_cost_view', 'is_check_cost_out_source', 'receiving_warehouse_id', 'partner_id')
    def onchange_is_check_cost_view_or_is_check_cost_out_source_or_purchase_order_product_id_or_partner_id(self):
        for rec in self:
            rec.invoice_line_ids = [(5, 0)]
            if rec.partner_id:
                invoice_line_ids = rec.invoice_line_ids.filtered(lambda line: line.product_id)  # Lọc các dòng có product_id
                if rec.receiving_warehouse_id:
                    product_cost = self.env['purchase.order'].search([('id', 'in', rec.purchase_order_product_id.ids)])
                    stock_cost = self.env['stock.picking'].search([('id', 'in', rec.receiving_warehouse_id.ids)])
                    if rec.is_check_cost_view:
                        rec.purchase_type = 'service'
                        for cost in product_cost.cost_line:
                            if not cost.product_id.categ_id and cost.product_id.categ_id.with_company(rec.company_id).property_stock_account_input_categ_id:
                                raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % cost.product_id.name)
                            else:
                                existing_line = invoice_line_ids.filtered(lambda line: line.product_id.id == cost.product_id.id)
                                if not existing_line:
                                    invoice_line_ids += self.env['account.move.line'].new({
                                        'product_id': cost.product_id.id,
                                        'description': cost.name,
                                        'price_unit': cost.vnd_amount,
                                        'cost_type': cost.product_id.detailed_type,
                                        'cost_id': cost.id,
                                    })
                                else:
                                    existing_line.price_unit += cost.vnd_amount
                            rec.invoice_line_ids = invoice_line_ids
                    elif rec.is_check_cost_out_source:
                        rec.purchase_type = 'service'
                        for out_source in product_cost.order_line_production_order:
                            for out_source_line in out_source.purchase_order_line_material_line_ids:
                                if out_source_line.product_id.product_tmpl_id.x_type_cost_product == 'labor_costs':
                                    if not out_source_line.product_id.categ_id and out_source_line.product_id.categ_id.with_company(
                                            rec.company_id).property_stock_account_input_categ_id:
                                        raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % out_source_line.product_id.name)
                                    else:
                                        existing_line = invoice_line_ids.filtered(lambda line: line.product_id.id == out_source_line.product_id.id)
                                        if not existing_line:
                                            invoice_line_ids += self.env['account.move.line'].new({
                                                'product_id': out_source_line.product_id.id,
                                                'description': out_source_line.name,
                                                'price_unit': out_source_line.product_id.standard_price,
                                                'cost_type': out_source_line.product_id.detailed_type,
                                                'cost_id': out_source_line.id,
                                            })
                                        else:
                                            existing_line.price_unit += out_source_line.product_id.standard_price
                                rec.invoice_line_ids = invoice_line_ids
                    else:
                        rec.purchase_type = 'product'
                        for product, pnk in zip(product_cost.order_line, stock_cost.move_line_ids_without_package):
                            if not product.product_id.categ_id and not product.product_id.categ_id.with_company(rec.company_id).property_stock_account_input_categ_id:
                                raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm của sản phẩm %s!!") % product.product_id.name)
                            else:
                                if str(product.id) == str(pnk.po_id):
                                    invoice_line_ids += self.env['account.move.line'].new({
                                        'product_id': product.product_id.id,
                                        'description': product.name,
                                        'request_code': product.request_purchases,
                                        'promotions': product.free_good,
                                        'quantity_purchased': pnk.quantity_purchase_done,
                                        'uom_id': pnk.purchase_uom.id,
                                        'exchange_quantity': pnk.quantity_change,
                                        'quantity': pnk.qty_done,
                                        'vendor_price': product.vendor_price,
                                        'price_unit': product.price_unit,
                                        'warehouse': product.location_id.id,
                                        'taxes_id': product.taxes_id.id,
                                        'tax_amount': product.price_tax,
                                        'price_subtotal': product.price_subtotal,
                                        'discount_percent': product.discount,
                                        'discount': product.discount_percent,
                                        'event_id': product.free_good,
                                        'work_order': product.production_id.id,
                                        'account_analytic_id': product.account_analytic_id.id,
                                        'cost_type': product.product_id.detailed_type,
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
            if rec.partner_id.is_passersby:
                vendor_back = self.env['vendor.back'].search([('vendor', '=', rec.partner_id.name),
                                                              ('vendor_back_id', '=', rec.id),
                                                              ('company_id', '=', rec.company_id.id),
                                                              ('code_tax', '=', rec.partner_id.vat),
                                                              ('street_ven', '=', rec.partner_id.street),
                                                              ], limit=1)
                rec.is_check_vendor_page = True
                if not vendor_back:
                    self.env['vendor.back'].create({'vendor': rec.partner_id.name,
                                                    'vendor_back_id': rec.id,
                                                    'company_id': rec.company_id.id,
                                                    'code_tax': rec.partner_id.vat,
                                                    'street_ven': rec.partner_id.street,
                                                    })
                else:
                    rec.vendor_back_ids = [(6, 0, vendor_back.id)]
            if not rec.partner_id.is_passersby:
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
                self.total_trade_discount = self.tax_totals.get('amount_total') / self.trade_discount

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
                        'product_id': line.product_id.id,
                        'description': line.description,
                        'price_unit': line.price_unit,
                        'quantity': line.quantity,
                        'before_tax': line.before_tax,
                        'discount': line.discount,
                        'synthetic_id': rec.id,
                    })
                    if synthetic_line:
                        synthetic_line.update({
                            'quantity': invoice.quantity,
                            'discount': invoice.discount_percent,
                            'price_unit': invoice.price_unit,
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
                if item.tax_amount > 0:
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
                if item.special_consumption_tax_amount > 0:
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
        account_tax = self.env['account.tax'].search([('company_id', '=', self.company_id.id),
                                                      ('type_tax_use', '=', 'purchase'),
                                                      ('active', '=', True),
                                                      ('code', '=', 'VATTNK')
                                                      ], limit=1)
        account_vat = []
        if not account_tax:
            raise ValidationError("Bạn chưa cấu hình thuế giá trị gia tăng nhập khẩu ở mục thuế!! Gợi ý mã mặc định của thuế giá trị gia tăng nhập khẩu: code = 'VATTNK'")
        else:
            if not self.env.ref('forlife_purchase.product_vat_tax').with_company(
                    self.company_id).property_account_expense_id:
                raise ValidationError("Bạn chưa cấu hình tài khoản chi phí kế toán thuế VAT (Nhập khẩu), trong sản phẩm có tên là Thuế VAT (Nhập khẩu) ở tab kế toán")
            for line in self.exchange_rate_line:
                account_credit_vat = (0, 0, {
                    'sequence': 9,
                    'account_id': self.env.ref('forlife_purchase.product_vat_tax').with_company(
                        self.company_id).property_account_expense_id.id,
                    'name': line.name,
                    'debit': 0,
                    'credit': line.vat_tax_amount * self.exchange_rate,
                })
                for nine, mine in zip(account_tax.refund_repartition_line_ids, account_tax.invoice_repartition_line_ids):
                    if not nine.product_id and nine.product_id.id == self.env.ref('forlife_purchase.product_vat_tax').id:
                        raise ValidationError(_("Bạn chưa gắn sản phẩm Thuế VAT (Nhập khẩu) trong mục thuế!! Gợi ý sản phẩm sẽ được gán vào trong bản ghi có mã code = 'VATTNK ở %s tab 'PHÂN PHỐI HOÀN TIỀN' dòng kèm thuế") % self.company_id.id)
                    if mine.repartition_type == 'tax' and nine.repartition_type == 'tax' and nine.product_id.id == self.env.ref('forlife_purchase.product_vat_tax').id:
                        if not mine.account_id:
                            raise ValidationError(_("Bạn chưa cấu hình tài khoản thuế trong mục thuế!! Gợi ý tài khoản được lấy ra từ bản ghi có mã code = 'VATTNK' ở %s tab 'PHÂN PHỐI CHO CÁC HÓA ĐƠN' dòng kèm thuế") % self.company_id.id)
                        account_debit_vat = (0, 0, {
                            'sequence': 99991,
                            'account_id': mine.account_id.id,
                            'name': 'thuế giá trị gia tăng nhập khẩu (VAT)',
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
    cost_type = fields.Char('')
    po_id = fields.Char('')
    ware_name = fields.Char('')
    type = fields.Selection(related="product_id.product_type", string='Loại mua hàng')
    work_order = fields.Many2one('forlife.production', string='Work Order')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    warehouse = fields.Many2one('stock.location', string='Whs')
    discount_percent = fields.Float(string='Chiết khấu', digits='Discount', default=0.0)
    discount = fields.Float(string='Chiết khấu %', digits='Discount', default=0.0)
    tax_amount = fields.Monetary(string='Tiền thuế')
    taxes_id = fields.Many2one('account.tax',
                               string='Thuế %',
                               domain=[('active', '=', True)])
    # price_unit = fields.Float(string='Unit Price',
    #                           digits='Product Price')

    # fields common !!
    readonly_discount = fields.Boolean(default=False)
    readonly_discount_percent = fields.Boolean(default=False)
    production_order = fields.Many2one('forlife.production', string='Production order')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")

    # goods invoice!!
    promotions = fields.Boolean(string='Promotions', default=False)
    quantity_purchased = fields.Integer(string='Quantity Purchased', default=1)
    exchange_quantity = fields.Float(string='Exchange Quantity')
    request_code = fields.Char('Mã phiếu yêu cầu')
    vendor_price = fields.Float(string='Vendor Price')
    # quantity = fields.Float(string='Quantity',
    #                         default=1.0, digits='Product Unit of Measure',
    #                         help="The optional quantity expressed by this line, eg: number of product sold. "
    #                              "The quantity is not a legal requirement but is very useful for some reports.",
    #                         compute='_compute_quantity', store=1)
    total_vnd_amount = fields.Float('Tổng tiền VNĐ', compute='_compute_total_vnd_amount', store=1)

    # asset invoice!!
    asset_code = fields.Char('Mã tài sản cố định')
    asset_name = fields.Char('Mô tả tài sản cố định')
    code_tax = fields.Char(string='Mã số thuế')
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")

    # field check exchange_quantity khi ncc vãng lại:
    is_check_exchange_quantity = fields.Boolean(default=False)

    # field check vendor_price khi ncc vãng lại:
    is_check_is_passersby = fields.Boolean(default=False)

    @api.depends('display_type', 'company_id')
    def _compute_account_id(self):
        res = super()._compute_account_id()
        for line in self:
            if line.product_id and line.move_id.purchase_order_product_id and line.move_id.purchase_order_product_id[0].is_inter_company == False:
                line.account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                line.name = line.product_id.name
        return res

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

    @api.depends('price_subtotal', 'move_id.exchange_rate', 'move_id')
    def _compute_total_vnd_amount(self):
        for rec in self:
            if rec.price_subtotal and rec.move_id.exchange_rate:
                rec.total_vnd_amount = rec.price_subtotal * rec.move_id.exchange_rate
    #
    # def _prepare_compute_all_values(self):
    #     # Hook method to returns the different argument values for the
    #     # compute_all method, due to the fact that discounts mechanism
    #     # is not implemented yet on the purchase orders.
    #     # This method should disappear as soon as this feature is
    #     # also introduced like in the sales module.
    #     self.ensure_one()
    #     return {
    #         'price_unit': self.price_unit,
    #         'currency': self.move_id.currency_id,
    #         'quantity': self.quantity,
    #         'product': self.product_id,
    #         'partner': self.move_id.partner_id,
    #     }
    #
    # @api.depends('quantity_purchased', 'exchange_quantity')
    # def _compute_quantity(self):
    #     for rec in self:
    #         if rec.quantity_purchased and rec.exchange_quantity:
    #             rec.quantity = rec.quantity_purchased * rec.exchange_quantity
    #         else:
    #             rec.quantity = rec.quantity_purchased
    #
    # @api.onchange("discount")
    # def _onchange_discount_percent(self):
    #     if not self.readonly_discount_percent:
    #         if self.discount:
    #             self.discount_percent = self.discount * self.price_unit * self.quantity * 0.01
    #
    #
    # @api.depends('taxes_id')
    # def _compute_tax_amount(self):
    #     for rec in self:
    #         if rec.taxes_id:
    #             rec.tax_amount = (rec.taxes_id.amount / 100) * rec.price_subtotal
    #             # self.readonly_discount = True
    #         # else:
    #             # self.readonly_discount = False
    #
    # # @api.onchange("discount_percent")
    # # def _onchange_discount(self):
    # #     if not self.readonly_discount:
    # #         if self.discount_percent:
    # #             self.readonly_discount_percent = True
    # #         else:
    # #             self.readonly_discount_percent = False
    #
    # # @api.depends('quantity', 'price_unit', 'taxes_id', 'promotions', 'discount', 'discount_percent')
    # # def _compute_amount(self):
    # #     for line in self:
    # #         tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
    # #         totals = list(tax_results['totals'].values())[0]
    # #         amount_untaxed = totals['amount_untaxed']
    # #         amount_tax = totals['amount_tax']
    # #
    # #         line.update({
    # #             'price_subtotal': amount_untaxed,
    # #             'tax_amount': amount_tax,
    # #             'price_total': amount_untaxed + amount_tax,
    # #         })
    #
    # def _convert_to_tax_base_line_dict(self):
    #     self.ensure_one()
    #     return self.env['account.tax']._convert_to_tax_base_line_dict(
    #         self,
    #         partner=self.move_id.partner_id,
    #         currency=self.move_id.currency_id,
    #         product=self.product_id,
    #         taxes=self.taxes_id,
    #         price_unit=self.price_unit,
    #         quantity=self.quantity,
    #         discount=self.discount,
    #         price_subtotal=self.price_subtotal,
    #     )
    #
    #
    # def _get_discounted_price_unit(self):
    #     self.ensure_one()
    #     if self.discount_percent:
    #         return self.price_unit - self.discount_percent
    #     else:
    #         return self.price_unit * (1 - self.discount / 100)
    #     return self.price_unit


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

    name = fields.Char(string='Tên sản phẩm')
    product_id = fields.Many2one('product.product', string='Mã sản phẩm')

    usd_amount = fields.Float(string='Thành tiền (USD)')  # đây chính là cột Thành tiền bên tab Sản phầm, a Trung đã viết trước
    vnd_amount = fields.Float(string='Thành tiền (VND)', compute='compute_vnd_amount', store=1)

    import_tax = fields.Float(string='% Thuế nhập khẩu')
    tax_amount = fields.Float(string='Tiền thuế nhập khẩu', compute='_compute_tax_amount', store=1)

    special_consumption_tax = fields.Float(string='% %Thuế tiêu thụ đặc biệt')
    special_consumption_tax_amount = fields.Float(string='Thuế tiêu thụ đặc biệt',
                                                  compute='_compute_special_consumption_tax_amount', store=1)

    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='Thuế GTGT', compute='_compute_vat_tax_amount', store=1)

    # total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Tổng tiền thuế', compute='compute_tax_amount', store=1)
    invoice_rate_id = fields.Many2one('account.move', string='Invoice Exchange Rate')
    qty_product = fields.Float(copy=True, string="Số lượng đặt mua")

    @api.constrains('import_tax', 'special_consumption_tax', 'vat_tax')
    def constrains_per(self):
        for item in self:
            if item.import_tax < 0:
                raise ValidationError('% thuế nhập khẩu phải >= 0 !')
            if item.special_consumption_tax < 0:
                raise ValidationError('% thuế tiêu thụ đặc biệt phải >= 0 !')
            if item.import_tax < 0:
                raise ValidationError('% thuế GTGT >= 0 !')

    @api.depends('usd_amount', 'invoice_rate_id.exchange_rate')
    def compute_vnd_amount(self):
        for rec in self:
            if not rec.invoice_rate_id.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id and not rec.invoice_rate_id.type_inv == 'tax':
                rec.vnd_amount = rec.usd_amount * rec.invoice_rate_id.exchange_rate
            else:
                pass

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
            self.exchange_rate = self.currency_id.rate

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

    description = fields.Char(string='Mã hàng')
    product_id = fields.Many2one('product.product', string='Tên hàng')
    product_uom = fields.Many2one(related='product_id.uom_id', string='ĐVT')
    price_unit = fields.Float(string='Đơn giá')
    quantity = fields.Float(string='Số lượng')
    price_subtotal = fields.Float(string='Thành tiền', compute='_compute_price_subtotal', store=1)
    discount = fields.Float(string='Chiết khấu')
    before_tax = fields.Float(string='Chi phí trước tính thuế', compute='_compute_is_check_pre_tax_costs', store=1)
    tnk_tax = fields.Float(string='Thuế nhập khẩu', compute='_compute_tnk_tax', store=1)
    db_tax = fields.Float(string='Thuế tiêu thụ đặc biệt', compute='_compute_db_tax', store=1)
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)', compute='_compute_is_check_pre_tax_costs', store=1)
    total_product = fields.Float(string='Tổng giá trị tiền hàng', compute='_compute_total_product', store=1)

    @api.depends('synthetic_id.cost_line.is_check_pre_tax_costs')
    def _compute_is_check_pre_tax_costs(self):
        for rec in self:
            cost_line_true = rec.synthetic_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            cost_line_false = rec.synthetic_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            total_cost_true = 0
            total_cost_false = 0
            for line in rec.synthetic_id.exchange_rate_line:
                if rec.synthetic_id.type_inv == 'tax':
                    if cost_line_true:
                        for item in cost_line_true:
                            if item.vnd_amount and rec.price_subtotal:
                                cost_host = ((rec.price_subtotal / sum(self.mapped('price_subtotal'))) * 100 / 100) * item.vnd_amount
                                total_cost_true += cost_host
                        rec.before_tax = total_cost_true
                    if cost_line_false:
                        for item in cost_line_false:
                            if rec.price_subtotal and rec.before_tax and item.vnd_amount:
                                cost_host = (((rec.price_subtotal + rec.before_tax + line.tax_amount + line.special_consumption_tax_amount) / (sum(self.mapped('price_subtotal')) + sum(self.mapped('before_tax')))) * 100 / 100) * item.vnd_amount
                                total_cost_false += cost_host
                        rec.after_tax = total_cost_false
                    if rec.product_id.id == line.product_id.id:
                        line.vnd_amount = rec.price_subtotal + rec.before_tax
                if rec.synthetic_id.type_inv == 'cost':
                    if rec.synthetic_id.cost_line:
                        for item in rec.synthetic_id.cost_line:
                            if item.vnd_amount and rec.price_subtotal:
                                cost_host = ((rec.price_subtotal / sum(self.mapped('price_subtotal'))) * 100 / 100) * item.vnd_amount
                                total_cost_true += cost_host
                        rec.before_tax = total_cost_true
                        rec.after_tax = rec.before_tax

    @api.depends('price_unit', 'quantity')
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.price_unit * record.quantity * record.synthetic_id.exchange_rate

    @api.depends('price_subtotal', 'discount', 'before_tax', 'tnk_tax', 'db_tax', 'after_tax')
    def _compute_total_product(self):
        for record in self:
            record.total_product = (record.price_subtotal - record.discount) + record.before_tax + record.tnk_tax + record.db_tax + record.after_tax

    @api.depends('synthetic_id.exchange_rate_line.tax_amount')
    def _compute_tnk_tax(self):
        for record in self:
            tnk_tax_total = 0.0
            for item in record.synthetic_id.exchange_rate_line:
                if record.product_id.id == item.product_id.id:
                    tnk_tax_total += item.tax_amount
            record.tnk_tax = tnk_tax_total

    @api.depends('synthetic_id.exchange_rate_line.special_consumption_tax_amount')
    def _compute_db_tax(self):
        for record in self:
            db_tax_total = 0.0
            for item in record.synthetic_id.exchange_rate_line:
                if record.product_id.id == item.product_id.id:
                    db_tax_total += item.special_consumption_tax_amount
            record.db_tax = db_tax_total
