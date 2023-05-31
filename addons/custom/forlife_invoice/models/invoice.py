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
    ], string='PO Type', default='product', required=1)
    number_bills = fields.Char(string='Number bills', copy=False, required=1)
    reference = fields.Char(string='Source Material')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 8), default=1)
    accounting_date = fields.Datetime(string='Accounting Date')
    payment_status = fields.Char(string='Payment onchange_purchase_typestatus')
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    is_check_cost_view = fields.Boolean(default=False, string='Hóa đơn chi phí')
    is_check_invoice_tnk = fields.Boolean(default=False)

    transportation_total = fields.Float(string='Tổng chi phí vận chuyển')
    loading_total = fields.Float(string='Tổng chi phí bốc dỡ')
    custom_total = fields.Float(string='Tổng chi phí thông quan')

    vendor_back_ids = fields.One2many('vendor.back', 'vendor_back_id', string='Vendor Back',
                                      compute='_compute_is_check_vendor_page', readonly=False)
    payment_term_invoice = fields.Many2one('account.payment.term', string='Chính sách thanh toán')
    type_inv = fields.Selection([('tax', 'Tax'), ('cost', 'Cost')])

    trade_discount = fields.Integer(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Integer(string='Tổng chiết khấu thương mại')

    # field domain cho 2 field đơn mua hàng và phiếu nhập kho
    receiving_warehouse_id = fields.Many2many('stock.picking', string='Receiving Warehouse')
    purchase_order_product_id = fields.Many2many('purchase.order', string='Purchase Order')
    partner_domain = fields.Char(compute='_compute_partner_domain')
    partner_domain_2 = fields.Char(compute='_compute_partner_domain_2')

    # field chi phí và thuế nhập khẩu
    exchange_rate_line = fields.One2many('invoice.exchange.rate', 'invoice_rate_id',
                                         string='Invoice Exchange Rate',
                                         compute='_compute_exchange_rate_line_and_cost_line',
                                         store=1)
    cost_line = fields.One2many('invoice.cost.line', 'invoice_cost_id',
                                string='Invoice Cost Line')

    # Field check k cho tạo addline khi hóa đơn đã có PO
    is_check = fields.Boolean(default=False)

    # Field check page ncc vãng lại
    is_check_vendor_page = fields.Boolean(default=False, compute='_compute_is_check_vendor_page')

    # tab e-invoice-bkav
    e_invoice_ids = fields.One2many('e.invoice', 'e_invoice_id', string='e Invoice')
    x_asset_fin = fields.Selection([
        ('TC', 'TC'),
        ('QC', 'QC'),
    ], string='Phân loại tài chính')

    x_root = fields.Selection([
        ('Intel ', 'Intel '),
        ('Winning', 'Winning'),
    ], string='Phân loại nguồn')

    # product_not_is_passersby = fields.Many2many('product.product')
    # tạo data lấy từ bkav về tab e-invoice

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
            if rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_2').id:
                data_search = self.env['purchase.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved'),
                     ('inventory_status', '=', 'done'), ('type_po_cost', '=', 'cost'), ('is_inter_company', '=', False)])
                rec.partner_domain = json.dumps([('id', 'in', data_search.ids)])
            elif rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id:
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

    @api.onchange('is_check_cost_view', 'purchase_order_product_id', 'partner_id', 'partner_id.group_id')
    def onchange_view_product_cost_and_receiving_warehouse_id(self):
        for rec in self:
            rec.invoice_line_ids = [(5, 0)]
            if rec.partner_id:
                receiving_warehouse = []
                invoice_line_ids = rec.invoice_line_ids.filtered(lambda line: line.product_id)  # Lọc các dòng có product_id
                if rec.purchase_order_product_id:
                    product_cost = self.env['purchase.order'].search(
                        [('id', 'in', rec.purchase_order_product_id.ids)])
                    for po in product_cost:
                        receiving_warehouse_id = self.env['stock.picking'].search(
                            [('origin', '=', po.name), ('location_dest_id', '=', po.location_id.id),
                             ('state', '=', 'done')])
                        if receiving_warehouse_id.picking_type_id.code == 'incoming':
                            for item in receiving_warehouse_id:
                                receiving_warehouse.append(item.id)
                                rec.receiving_warehouse_id = [(6, 0, receiving_warehouse)]
                    if rec.is_check_cost_view:
                        rec.purchase_type = 'service'
                        for cost in product_cost.cost_line:
                            if not cost.product_id.categ_id and cost.product_id.categ_id.with_company(rec.company_id).property_stock_account_input_categ_id:
                                raise ValidationError("Chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm!!")
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
                    else:
                        rec.purchase_type = 'product'
                        for product in product_cost.order_line:
                            if not product.product_id.categ_id and not product.product_id.categ_id.with_company(rec.company_id).property_stock_account_input_categ_id:
                                raise ValidationError("Chưa cấu hình tài khoản nhập kho ở danh mục sản phẩm!!")
                            else:
                                invoice_line_ids += self.env['account.move.line'].new({
                                    'product_id': product.product_id.id,
                                    'description': product.name,
                                    'request_code': product.request_purchases,
                                    'promotions': product.free_good,
                                    'quantity_purchased': product.purchase_quantity,
                                    'uom_id': product.purchase_uom.id,
                                    'exchange_quantity': product.exchange_quantity,
                                    'quantity': product.product_qty,
                                    'vendor_price': product.vendor_price,
                                    'price_unit': product.price_unit,
                                    'warehouse': product.location_id.id,
                                    'taxes_id': product.taxes_id.id,
                                    'tax_amount': product.price_tax,
                                    'price_subtotal': product.price_subtotal,
                                    'discount_percent': product.discount_percent,
                                    'discount': product.discount,
                                    'event_id': product.free_good,
                                    'work_order': product.production_id.id,
                                    'account_analytic_id': product.account_analytic_id.id,
                                    'cost_type': product.product_id.detailed_type,
                                })
                        rec.invoice_line_ids = invoice_line_ids
                else:
                    rec.receiving_warehouse_id = False
                    if rec.is_check_cost_view:
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
        context_invoice = self._context
        old_line_count = len(self.invoice_line_ids)
        new_line_count = len(vals.get('invoice_line_ids', []))
        res = super(AccountMove, self).write(vals)
        for rec in self:
            if rec.is_check_cost_view:
                for line in rec.invoice_line_ids:
                    if line.product_id and line.display_type == 'product':
                        line.write({
                            'account_id': line.product_id.categ_id.with_company(
                                line.company_id).property_stock_account_input_categ_id.id,
                            'name': line.product_id.name
                        })
        for key, value in context_invoice.items():
            print(key, value)
            if value == "purchase.order":
                if (new_line_count > old_line_count) and self.state == "draft":
                    raise ValidationError('Không thể thêm sản phẩm khi ở trạng thái dự thảo')
                else:
                    return rec
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
                                                              ])
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

    @api.constrains('exchange_rate', 'trade_discount', 'number_bills')
    def constrains_exchange_rare(self):
        for item in self:
            if item.exchange_rate < 0:
                raise ValidationError('Tỷ giá không được âm!')
            if item.trade_discount < 0:
                raise ValidationError('Chiết khấu thương mại không được âm!')
            # if not item.number_bills or not check_length_255(item.number_bills):
            #     raise ValidationError(_("Số hóa đơn không hợp lệ!!"))

    @api.onchange('trade_discount')
    def onchange_total_trade_discount(self):
        if self.trade_discount:
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_total') / self.trade_discount

    @api.depends('purchase_order_product_id', 'purchase_order_product_id.exchange_rate_line', 'invoice_line_ids')
    def _compute_exchange_rate_line_and_cost_line(self):
        exchange_rate = self.env['invoice.exchange.rate']
        for rec in self:
            rec.exchange_rate_line = [(5, 0)]
            if rec.partner_id.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_1').id or rec.type_inv == 'tax':
                for po in rec.purchase_order_product_id:
                    for exchange in po.exchange_rate_line:
                        exchange_rate.create({
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

    def create_invoice_tnk_db(self):
        for rec in self:
            account_db = []
            account_tnk = []
            if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id \
                    or not self.env.ref('forlife_purchase.product_import_tax_default').with_company(rec.company_id).property_account_expense_id:
                raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế nhập khẩu hoặc tài khoản chi phí kế toán")
            if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id \
                    or not self.env.ref('forlife_purchase.product_excise_tax_default').with_company(rec.company_id).property_account_expense_id:
                raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục thuế tiêu thụ đặc biệt hoặc tài khoản chi phí kế toán")
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
                account_credit_db = (0, 0, {
                    'sequence': 99991,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        rec.company_id).property_account_expense_id.id,
                    'name': self.env.ref('forlife_purchase.product_excise_tax_default').with_company(
                        rec.company_id).property_account_expense_id.name,
                    'debit': 0,
                    'credit': item.special_consumption_tax_amount * self.exchange_rate,
                })
                account_debit_tnk = (0, 0, {
                    'sequence': 9,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.tax_amount * self.exchange_rate,
                    'credit': 0,
                })
                account_debit_db = (0, 0, {
                    'sequence': 9,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.with_company(rec.company_id).property_stock_account_input_categ_id.id,
                    'name': item.product_id.name,
                    'debit': item.special_consumption_tax_amount * self.exchange_rate,
                    'credit': 0,
                })

                lines_tnk = [account_debit_tnk, account_credit_tnk]
                lines_db = [account_debit_db, account_credit_db]
                account_db.extend(lines_db)
                account_tnk.extend(lines_tnk)
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
                'ref': (_('Hóa đơn thuế tiêu thụ đặc biệt %s') % self.name),
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': f"Hóa đơn thuế tiêu thụ đặc biệt",
                'line_ids': merged_records_list_db,
                'move_type': 'entry',
            })
            invoice_db.action_post()
            invoice_tnk = self.create({
                'ref': (_('Hóa đơn thuế nhập khẩu %s') % self.name),
                'is_check_invoice_tnk': True,
                'invoice_date': self.invoice_date,
                'invoice_description': f"Hóa đơn thuế nhập khẩu",
                'line_ids': merged_records_list_tnk,
                'move_type': 'entry',
            })
            invoice_tnk.action_post()

    def create_tax_vat(self):
        account_tax = self.env['account.tax'].search([('company_id', '=', self.company_id.id),
                                                      ('type_tax_use', '=', 'purchase'),
                                                      ('active', '=', True),
                                                      ('name', '=', 'Thuế GTGT hàng nhập khẩu')
                                                      ], limit=1)
        account_vat = []
        if not self.env.ref('forlife_purchase.product_vat_tax').with_company(self.company_id).property_account_expense_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản chi phí kế toán thuế VAT (Nhập khẩu)")
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
                if mine.repartition_type == 'tax' and nine.repartition_type == 'tax' and nine.product_id.id == self.env.ref('forlife_purchase.product_vat_tax').id:
                    if not mine.account_id:
                        raise ValidationError("Bạn chưa cấu hình tài khoản thuế trong cấu hình thuế GTGT hàng Nhập khẩu")
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
            'ref': 'Hóa đơn thuế giá trị gia tăng VAT (Nhập khẩu)',
            'is_check_invoice_tnk': True,
            'invoice_date': self.invoice_date,
            'invoice_description': f"Hóa đơn thuế giá trị gia tăng VAT (Nhập khẩu)",
            'line_ids': merged_records_list_vat,
            'move_type': 'entry',
        })
        invoice_vat.action_post()

    def create_trade_discount(self):
        account_ck = []
        if not self.env.ref('forlife_purchase.product_discount_tax').categ_id.with_company(self.company_id).property_stock_account_input_categ_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản trong danh mục chiết khấu")
        if not self.partner_id.property_account_receivable_id:
            raise ValidationError("Bạn chưa cấu hình tài khoản trong nhà cung cấp")
        account_331 = (0, 0, {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'name': self.partner_id.property_account_receivable_id.name,
            'debit': self.total_trade_discount * self.exchange_rate,
            'credit': 0,
        })
        account_771 = (0, 0, {
            'account_id': self.env.ref('forlife_purchase.product_discount_tax').categ_id.with_company(
                self.company_id).property_stock_account_input_categ_id.id,
            'name': self.env.ref('forlife_purchase.product_discount_tax').categ_id.with_company(
                self.company_id).property_stock_account_input_categ_id.name,
            'debit': 0,
            'credit': self.total_trade_discount * self.exchange_rate,
        })
        lines_ck = [account_331, account_771]
        account_ck.extend(lines_ck)

        invoice_ck = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'ref': 'Hóa đơn chiết khấu ',
            'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') else False,
            'invoice_date': self.invoice_date,
            'invoice_description': f"Hóa đơn chiết khấu",
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
    discount_percent = fields.Float(string='Chiết khấu (%)', digits='Discount', default=0.0)
    discount = fields.Float(string='Chiết khấu', digits='Discount', default=0.0)
    tax_amount = fields.Monetary(string='Tiền thuế', compute='_compute_tax_amount', store=1)
    taxes_id = fields.Many2one('account.tax',
                               string='Thuế %',
                               domain=[('active', '=', True)])
    price_unit = fields.Float(string='Unit Price',
                              digits='Product Price')

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
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.",
                            compute='_compute_quantity', store=1)
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
            # is_check_partner_id = self.env['account.move'].browse(line.get('move_id')).partner_id.group_id.id
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

    # @api.depends('vendor_price', 'exchange_quantity',
    #              'move_id', 'move_id.is_check_cost_view',
    #              'move_id.partner_id', 'promotions',
    #              'product_id')
    # def _compute_price_unit(self):
    #     for rec in self:
    #         price_sup_qty_min = self.env['product.supplierinfo'].search(
    #             [('partner_id', '=', rec.move_id.partner_id.id), ('product_id', '=', rec.product_id.id)],
    #             limit=1)
    #         if rec.partner_id:
    #             if not rec.move_id.is_check_cost_view:
    #                 if not rec.partner_id.is_passersby:
    #                     rec.exchange_quantity = price_sup_qty_min.min_qty
    #                     if rec.promotions:
    #                         rec.vendor_price = 0
    #                     else:
    #                         rec.vendor_price = price_sup_qty_min.price
    #                 else:
    #                     rec.is_check_exchange_quantity = True
    #                     if rec.promotions:
    #                         rec.is_check_is_passersby = True
    #                         rec.vendor_price = 0
    #                     else:
    #                         rec.is_check_is_passersby = True
    #                         rec.vendor_price = 0
    #                 if rec.vendor_price and rec.exchange_quantity:
    #                     rec.price_unit = rec.vendor_price / rec.exchange_quantity
    #                 else:
    #                     pass
    #             else:
    #                 pass

    @api.depends('quantity', 'price_unit', 'taxes_id')
    def _compute_tax_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())
            line.update({
                'tax_amount': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency': self.move_id.currency_id,
            'quantity': self.quantity,
            'product': self.product_id,
            'partner': self.move_id.partner_id,
        }

    @api.depends('quantity_purchased', 'exchange_quantity')
    def _compute_quantity(self):
        for rec in self:
            if rec.quantity_purchased and rec.exchange_quantity:
                rec.quantity = rec.quantity_purchased * rec.exchange_quantity
            else:
                rec.quantity = rec.quantity_purchased

    @api.onchange('quantity', 'price_unit', 'discount')
    def _onchange_price_unit_quantity_discount(self):
        if self.quantity and self.price_unit:
            self.price_subtotal = (self.price_unit * self.quantity) - self.discount

    @api.onchange("discount_percent")
    def _onchange_discount_percent(self):
        if not self.readonly_discount_percent:
            if self.discount_percent:
                self.discount = self.discount_percent * self.price_unit * self.quantity * 0.01
                self.readonly_discount = True
            else:
                self.readonly_discount = False

    @api.onchange("discount")
    def _onchange_discount(self):
        if not self.readonly_discount:
            if self.discount:
                self.discount_percent = (self.discount / self.price_unit) * 100 if self.price_unit else 0
                self.readonly_discount_percent = True
            else:
                self.readonly_discount_percent = False

    @api.depends('quantity', 'price_unit', 'taxes_id', 'promotions', 'discount', 'discount_percent')
    def _compute_amount(self):
        if self.move_type == 'in_invoice':
            for line in self:
                tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed = totals['amount_untaxed']
                amount_tax = totals['amount_tax']

                line.update({
                    'price_subtotal': amount_untaxed,
                    'tax_amount': amount_tax,
                    'price_total': amount_untaxed + amount_tax,
                })

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        if self.move_type == 'in_invoice':
            return self.env['account.tax']._convert_to_tax_base_line_dict(
                self,
                partner=self.move_id.partner_id,
                currency=self.move_id.currency_id,
                product=self.product_id,
                taxes=self.taxes_id,
                price_unit=self.price_unit,
                quantity=self.quantity,
                discount=self.discount_percent,
                price_subtotal=self.price_subtotal,
            )

    def _get_discounted_price_unit(self):
        self.ensure_one()
        if self.move_type == 'in_invoice':
            if self.discount:
                return self.price_unit - self.discount
            else:
                return self.price_unit * (1 - self.discount_percent / 100)
            return self.price_unit


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
    tax_back = fields.Float(string='Tiền thuế', compute='compute_tax_percent_back', store=1)
    tax_percent_back = fields.Float(string='% Thuế')
    totals_back = fields.Float(string='Tổng tiền sau thuế', compute='compute_totals_back', store=1)

    @api.constrains('vendor', 'code_tax', 'street_ven', 'company_id', 'invoice_reference', 'invoice_description')
    def constrains_check_duplicate(self):
        for record in self:
            if record.vendor and record.street_ven and record.search_count(
                    [('vendor', '=', record.vendor),
                     ('code_tax', '=', record.code_tax),
                     ('street_ven', '=', record.street_ven),
                     ('company_id', '=', record.company_id.id),
                     ('invoice_reference', '=', record.invoice_reference),
                     ('invoice_description', '=', record.invoice_description),
                     ('id', '!=', record.id)]) > 1:
                raise ValidationError(_('Nhà cung cấp vãng lai đã tồn tại !!'))

    @api.constrains('price_subtotal_back')
    def constrains_check_less_than(self):
        for rec in self:
            if rec.price_subtotal_back < 0:
                raise ValidationError(_('Bạn không được nhập thành tiền nhỏ hơn 0 !!'))

    @api.depends("tax_percent_back")
    def compute_tax_percent_back(self):
        for rec in self:
            if rec.tax_percent_back:
                rec.tax_back = rec.tax_percent_back * rec.price_subtotal_back * 0.01

    @api.depends('tax_back', 'price_subtotal_back')
    def compute_totals_back(self):
        for rec in self:
            rec.totals_back = rec.price_subtotal_back + rec.tax_back

    @api.constrains('totals_back', 'vendor_back_id.total_tax')
    def constrains_vendor_back_by_invocie(self):
        for rec in self:
            sum_subtotal = sum(rec.vendor_back_id.invoice_line_ids.mapped('price_subtotal'))
            sum_tax = sum(rec.vendor_back_id.invoice_line_ids.mapped('tax_amount')) if rec.vendor_back_id.invoice_line_ids.mapped('tax_amount') else 0
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

    product_id = fields.Many2one('product.product', string='Sản phẩm')
    name = fields.Char(string='Mô tả', related='product_id.name')
    transportation_costs_percent = fields.Float(string='% Chi phí vận chuyển')
    transportation_costs = fields.Float(string='Chi phí vận chuyển', compute='compute_transportation_costs')
    loading_costs_percent = fields.Float(string='% Chi phí bốc dỡ')
    loading_costs = fields.Float(string='Chi phí bốc dỡ ', compute='compute_loading_costs')
    custom_costs_percent = fields.Float(string='% Chi phí thông quan')
    custom_costs = fields.Float(string='Chi phí thông quan', compute='compute_custom_costs')

    invoice_cost_id = fields.Many2one('account.move', string='Invoice Cost Line')

    @api.depends('invoice_cost_id.transportation_total', 'transportation_costs_percent')
    def compute_transportation_costs(self):
        for rec in self:
            rec.transportation_costs = rec.invoice_cost_id.transportation_total * rec.transportation_costs_percent

    @api.depends('invoice_cost_id.loading_total', 'loading_costs_percent')
    def compute_loading_costs(self):
        for rec in self:
            rec.loading_costs = rec.invoice_cost_id.loading_total * rec.loading_costs_percent

    @api.depends('invoice_cost_id.custom_total', 'custom_costs_percent')
    def compute_custom_costs(self):
        for rec in self:
            rec.custom_costs = rec.invoice_cost_id.custom_total * rec.custom_costs_percent


class eInvoice(models.Model):
    _name = 'e.invoice'
    _description = 'e Invoice'

    e_invoice_id = fields.Many2one('account.move', string='e invoice')

    number_e_invoice = fields.Char('Số HĐĐT')
    date_start_e_invoice = fields.Char('Ngày phát hành HĐĐT')
    state_e_invoice = fields.Char('Trạng thái HĐĐT', related='e_invoice_id.invoice_state_e')
