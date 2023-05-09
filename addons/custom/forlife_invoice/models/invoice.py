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
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', required=1)
    purchase_type = fields.Selection([
        ('product', 'Goods'),
        ('asset', 'Asset'),
        ('service', 'Service'),
    ], string='PO Type', default='product', required=1)
    number_bills = fields.Char(string='Number bills', copy=False)
    reference = fields.Char(string='Source Material')
    exchange_rate = fields.Float(string="Exchange Rate", default=1)
    accounting_date = fields.Datetime(string='Accounting Date')
    payment_status = fields.Char(string='Payment status')
    is_check_cost_view = fields.Boolean(default=False, string='Hóa đơn chi phí')


    transportation_total = fields.Float(string='Tổng chi phí vận chuyển')
    loading_total = fields.Float(string='Tổng chi phí bốc dỡ')
    custom_total = fields.Float(string='Tổng chi phí thông quan')

    # purchase_order_id = fields.Many2one('purchase.order', string="Auto-Complete")
    vendor_back_ids = fields.One2many('vendor.back', 'vendor_back_id', string='Vendor Back', compute='_compute_is_check_vendor_page', readonly=False)
    payment_term_invoice = fields.Many2one('account.payment.term', string='Chính sách thanh toán')

    trade_discount = fields.Float(string='Chiết khấu thương mại(%)', compute='_compute_total_trade_discount_and_trade_discount', store=1)
    total_trade_discount = fields.Float(string='Tổng chiết khấu thương mại', compute='_compute_total_trade_discount_and_trade_discount', store=1)

    ## field domain cho 2 field đơn mua hàng và phiếu nhập kho
    receiving_warehouse_id = fields.Many2many('stock.picking', string='Receiving Warehouse')
    purchase_order_product_id = fields.Many2many('purchase.order', string='Purchase Order')
    partner_domain = fields.Char(compute='_compute_partner_domain')

    ## field chi phí và thuế nhập khẩu
    exchange_rate_line = fields.One2many('invoice.exchange.rate', 'invoice_rate_id',
                                         string='Invoice Exchange Rate',
                                         store=1)
    cost_line = fields.One2many('invoice.cost.line', 'invoice_cost_id',
                                string='Invoice Cost Line',
                                store=1)

    # Field check k cho tạo addline khi hóa đơn đã có PO
    is_check = fields.Boolean(default=False)

    # Field check page ncc vãng lại
    is_check_vendor_page = fields.Boolean(default=False, compute='_compute_is_check_vendor_page')

    ##domain product_cost:
    product_product_mm = fields.Many2many('product.product', store=1)

    ##tab e-invoice-bkav
    e_invoice_ids = fields.One2many('e.invoice', 'e_invoice_id', string='e Invoice',
                                    compute='_compute_e_invoice_ids_exists_bkav')
    x_asset_fin = fields.Selection([
        ('TC', 'TC'),
        ('QC', 'QC'),
    ], string='Phân loại tài chính')
    x_root = fields.Selection([
        ('Intel ', 'Intel '),
        ('Winning', 'Winning'),
    ], string='Phân loại nguồn')
    @api.depends('exists_bkav')
    def _compute_e_invoice_ids_exists_bkav(self):
        for rec in self:
            data_e_invoice = self.env['e.invoice'].search([('e_invoice_id', '=', rec.id)], limit=1)
            if rec.exists_bkav:
                self.env['e.invoice'].create({
                    'number_e_invoice': rec.invoice_no,
                    'date_start_e_invoice': rec.create_date,
                    'state_e_invoice': rec.invoice_state_e,
                    'e_invoice_id': rec.id,
                })
            rec.e_invoice_ids = [(6, 0, data_e_invoice.ids)]

    @api.depends('partner_id')
    def _compute_partner_domain(self):
        self = self.sudo()
        for rec in self:
            data_search = self.env['purchase.order'].search(
                [('partner_id', '=', rec.partner_id.id), ('custom_state', '=', 'approved')])
            rec.partner_domain = json.dumps([('id', 'in', data_search.ids)])

    @api.onchange('partner_id')
    def onchange_partner_domain(self):
        self.purchase_order_product_id = [(5, 0)]
        self.invoice_line_ids = [(5, 0)]

    @api.onchange('is_check_cost_view', 'purchase_order_product_id', 'partner_id')
    def onchange_view_product_cost_and_receiving_warehouse_id(self):
        self.invoice_line_ids = [(5, 0)]
        invoice_cost = self.env['product.product'].search([('detailed_type', '=', 'service')])
        invoice_cost_2 = self.env['product.product'].search([])
        id_account_move = self.env['account.move'].search([], order='id desc', limit=1).id
        for rec in self:
            if rec.partner_id:
                rec.product_product_mm = [(6, 0, invoice_cost_2.ids)]
                receiving_warehouse = []
                if rec.purchase_order_product_id:
                    for po in rec.purchase_order_product_id:
                        last_id = str(rec.purchase_order_product_id[-1].id).split("_")[1]
                        receiving_warehouse_id = self.env['stock.picking'].search(
                            [('origin', '=', po.name), ('location_dest_id', '=', po.location_id.id)])
                        receiving_warehouse.append(receiving_warehouse_id.id)
                    rec.receiving_warehouse_id = [(6, 0, receiving_warehouse)]
                    for cost in rec.purchase_order_product_id.cost_line:
                        last_cost_id = str(cost[-1].id).split("_")[1]
                        move_cost_line = self.env['account.move.line'].search(
                            [('product_id', '=', cost.product_id.id),
                             ('description', '=', cost.name),
                             ('move_id', '=', id_account_move),
                             ('cost_type', '=', cost.product_id.detailed_type),
                             ('cost_line_id', '=', last_cost_id),
                             ])
                        if not move_cost_line:
                            move_cost_line.create({
                                'product_id': cost.product_id.id,
                                'description': cost.name,
                                'price_unit': cost.expensive_total,
                                'move_id': id_account_move,
                                'company_id': rec.journal_id.company_id or rec.company_id or self.env.company,
                                'cost_type': cost.product_id.detailed_type,
                                'cost_line_id': last_cost_id,
                                'po_id': last_id,
                                'account_id': cost.product_id.property_account_expense_id.id,
                            })
                        else:
                            pass
                    account_line = self.env['account.move.line'].search([('cost_type', '=', 'service'), ('po_id', 'in', rec.purchase_order_product_id.ids)])
                    if rec.is_check_cost_view:
                        rec.purchase_type = 'service'
                        rec.invoice_line_ids = [(6, 0, account_line.ids)]
                        rec.product_product_mm = [(6, 0, invoice_cost.ids)]
                    else:
                        rec.purchase_type = 'product'
                        rec.product_product_mm = [(6, 0, invoice_cost_2.ids)]
                else:
                    rec.receiving_warehouse_id = False
                    if rec.is_check_cost_view:
                        rec.purchase_type = 'service'
                        rec.product_product_mm = [(6, 0, invoice_cost.ids)]
                    else:
                        rec.purchase_type = 'product'
                        rec.product_product_mm = [(6, 0, invoice_cost_2.ids)]

    @api.onchange('invoice_line_ids')
    def onchange_partner_domain(self):
        self.exchange_rate_line = [(5, 0)]
        self.cost_line = [(5, 0)]
        for line in self.invoice_line_ids:
            self.env['invoice.exchange.rate'].create({
                'product_id': line.product_id.id,
                'name': line.description,
                'usd_amount': line.price_subtotal,
                'invoice_rate_id': self.id
            })
            self.env['invoice.cost.line'].create({
                'product_id': line.product_id.id,
                'name': line.description,
                'invoice_cost_id': self.id
            })

    @api.depends('partner_id.is_passersby', 'partner_id')
    def _compute_is_check_vendor_page(self):
        for rec in self:
            vendor_back = self.env['vendor.back'].search([('vendor', '=', rec.partner_id.name),
                                                ('vendor_back_id', '=', rec.vendor_back_ids.id),
                                                ('code_tax', '=', rec.partner_id.vat),
                                                ('street_ven', '=', rec.partner_id.street)])
            if rec.partner_id.is_passersby:
                rec.is_check_vendor_page = True
                if not vendor_back:
                    self.env['vendor.back'].create({'vendor': rec.partner_id.name,
                                                    'vendor_back_id': rec.vendor_back_ids.id,
                                                    'code_tax': rec.partner_id.vat,
                                                    'street_ven': rec.partner_id.street})
                else:
                    rec.vendor_back_ids = [(6, 0, vendor_back.id)]
            if not rec.partner_id.is_passersby:
                rec.is_check_vendor_page = False

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.purchase_type = self.purchase_order_id.purchase_type

    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
        order_invoice_line_ids = []
        for line in self.invoice_line_ids:
            if line.product_type == self.purchase_type:
                order_invoice_line_ids.append(line.id)
        self.write({
            'invoice_line_ids': [(6, 0, order_invoice_line_ids)]
        })

    @api.constrains('exchange_rate', 'trade_discount', 'number_bills','invoice_line_ids')
    def constrains_exchange_rare(self):
        for item in self:
            if item.exchange_rate < 0:
                raise ValidationError('Tỷ giá không được âm!')
            if item.trade_discount < 0:
                raise ValidationError('Chiết khấu thương mại không được âm!')
            if item.number_bills:
                if not item.number_bills:
                    raise ValidationError(_("Số hóa đơn không hợp lệ!!"))
                elif not check_length_255(item.number_bills):
                    raise ValidationError(_('Số hóa đơn không được dài hơn 255 ký tự!!'))
                else:
                    return False

    is_check_total_and_trade_discount = fields.Boolean('', compute='_compute_total_trade_discount_and_trade_discount' ,store=1)

    @api.depends('trade_discount', 'total_trade_discount')
    def _compute_total_trade_discount_and_trade_discount(self):
        for item in self:
            if item.tax_totals and item.tax_totals and item.tax_totals.get('amount_total') and item.tax_totals.get(
                    'amount_total', 0) != 0:
                item.total_trade_discount = item.tax_totals.get('amount_total') * (item.trade_discount / 100)
                if item.total_trade_discount:
                    item.trade_discount = False
                    item.is_check_total_and_trade_discount = True
                else:
                    if item.trade_discount:
                        item.trade_discount = (item.total_trade_discount / item.tax_totals.get(
                            'amount_total')) * 100
                        item.is_check_total_and_trade_discount = False

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    move_id = fields.Many2one('account.move', string='Journal Entry',
                              index=True, required=False, readonly=True, auto_join=True, ondelete="cascade",
                              check_company=True,
                              help="The move of this entry line.")
    cost_line_id = fields.Char()
    cost_type = fields.Char('')
    po_id = fields.Char()
    type = fields.Selection(related="product_id.detailed_type")
    work_order = fields.Many2one('forlife.production', string='Work Order')
    current_user = fields.Many2one('res.users', default=lambda self: self.env.user, string='Account', required=1)
    uom_id = fields.Many2one('uom.uom', string='Uom')
    warehouse = fields.Many2one('stock.location', string='Whs')
    discount = fields.Float(string='Discount (%)',
                            digits='Discount',
                            default=0.0,
                            compute='_compute_discount',
                            store=1,
                            readonly=0)
    discount_invoice = fields.Float(string='Discount',
                                    digits='Discount',
                                    default=0.0,
                                    compute='_compute_discount_invoice',
                                    store=1,
                                    readonly=0)
    tax_amount = fields.Monetary(string='Tiền thuế',
                                 compute='_compute_tax_amount',
                                 store=1)
    taxes_id = fields.Many2one('account.tax',
                               string='Thuế %',
                               domain=[('active', '=', True)])
    price_unit = fields.Float(string='Unit Price',
                              digits='Product Price',
                              compute='_compute_price_unit',
                              store=1)

    ## fields common !!
    production_order = fields.Many2one('forlife.production', string='Production order')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")


    ## goods invoice!!
    promotions = fields.Boolean(string='Promotions', default=False)
    quantity_purchased = fields.Integer(string='Quantity Purchased', default=1)
    exchange_quantity = fields.Float(string='Exchange Quantity', compute='_compute_value_exchange_quantity_vendor_price', store=1, readonly= False)
    request_code = fields.Char('Mã phiếu yêu cầu')
    vendor_sup_invoice = fields.Many2one(related='move_id.partner_id', store=1)
    vendor_price = fields.Float(string='Vendor Price', compute='_compute_value_exchange_quantity_vendor_price', store=1)
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.",
                            compute='_compute_quantity', store=1)

    ## asset invoice!!
    asset_code = fields.Char('Mã tài sản cố định')
    asset_name = fields.Char('Mô tả tài sản cố định')
    code_tax = fields.Char(string='Mã số thuế')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")

    #field check exchange_quantity khi ncc vãng lại:
    is_check_exchange_quantity = fields.Boolean(default=False)

    #field check vendor_price khi ncc vãng lại:
    is_check_is_passersby = fields.Boolean(default=False)

    @api.depends('move_id.partner_id', 'promotions', 'product_id')
    def _compute_value_exchange_quantity_vendor_price(self):
        for rec in self:
            ex_sup_invoice_promo = self.env['res.partner'].search(
                [('name', '=', rec.vendor_sup_invoice.name)], limit=1)
            price_sup_qty_min = self.env['product.supplierinfo'].search(
                [('partner_id', '=', rec.vendor_sup_invoice.id), ('product_id', '=', rec.product_id.id)],
                limit=1)
            if ex_sup_invoice_promo and ex_sup_invoice_promo.is_passersby:
                rec.is_check_exchange_quantity = True
            if ex_sup_invoice_promo and not ex_sup_invoice_promo.is_passersby:
                rec.exchange_quantity = price_sup_qty_min.min_qty
            if ex_sup_invoice_promo.is_passersby and rec.promotions:
                rec.is_check_is_passersby = True
                rec.vendor_price = 0
            if ex_sup_invoice_promo.is_passersby and not rec.promotions:
                rec.is_check_is_passersby = True
                rec.vendor_price = 0
            if not ex_sup_invoice_promo.is_passersby and rec.promotions:
                rec.vendor_price = 0
            if not ex_sup_invoice_promo.is_passersby and not rec.promotions:
                rec.vendor_price = price_sup_qty_min.price

    @api.depends('vendor_price', 'exchange_quantity')
    def _compute_price_unit(self):
        for rec in self:
            if rec.vendor_price and rec.exchange_quantity:
                rec.price_unit = rec.vendor_price / rec.exchange_quantity
            else:
                rec.price_unit = rec.vendor_price

    @api.depends('quantity_purchased', 'exchange_quantity')
    def _compute_quantity(self):
        for rec in self:
            if rec.quantity_purchased and rec.exchange_quantity:
                rec.quantity = rec.quantity_purchased * rec.exchange_quantity
            else:
                rec.quantity = rec.quantity_purchased

    @api.depends('taxes_id.amount', 'price_subtotal')
    def _compute_tax_amount(self):
        for rec in self:
            if rec.price_subtotal and rec.taxes_id:
                rec.tax_amount = rec.price_subtotal * (rec.taxes_id.amount / 100)

    @api.depends('price_unit', 'discount')
    def _compute_discount_invoice(self):
        for rec in self:
            if rec.price_unit and rec.discount:
                rec.discount_invoice = rec.discount * rec.price_unit

    @api.depends('discount_invoice', 'price_unit')
    def _compute_discount(self):
        for rec in self:
            if rec.discount_invoice and rec.price_unit:
                rec.discount = (rec.discount_invoice / rec.price_unit) * 100

    @api.depends('quantity', 'price_unit', 'taxes_id', 'promotions', 'discount', 'discount_invoice')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_price_subtotal = (line.price_unit * line.exchange_quantity) - line.discount_invoice
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_price_subtotal,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.move_id.partner_id,
            currency=self.move_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.quantity,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

class RespartnerVendor(models.Model):
    _name = "vendor.back"

    vendor_back_id = fields.Many2one('account.move', ondelete='cascade')
    vendor = fields.Char('Tên nhà cung cấp')
    code_tax = fields.Char('MST')
    street_ven = fields.Char('Địa chỉ')

    @api.constrains('vendor', 'code_tax', 'street_ven')
    def constrains_check_duplicate(self):
        for record in self:
            if record.vendor and record.street_ven and record.search_count(
                    [('vendor', '=', record.vendor),
                     ('code_tax', '=', record.code_tax),
                     ('street_ven', '=', record.street_ven)]) > 1:
                raise ValidationError(_('Nhà cung cấp đã tồn tại !!'))

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
    special_consumption_tax_amount = fields.Float(string='Thuế tiêu thụ đặc biệt', compute='_compute_special_consumption_tax_amount', store=1)

    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='Thuế GTGT', compute='_compute_vat_tax_amount', store=1)

    # total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Tổng tiền thuế', compute='compute_tax_amount', store=1)
    invoice_rate_id = fields.Many2one('account.move', string='Invoice Exchange Rate')

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
            rec.vnd_amount = rec.usd_amount * rec.invoice_rate_id.exchange_rate

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
            rec.total_tax_amount = rec.vnd_amount + rec.tax_amount + rec.special_consumption_tax_amount + rec.vat_tax_amount

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

