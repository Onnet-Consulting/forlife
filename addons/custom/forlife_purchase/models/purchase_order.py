from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import json
from lxml import etree


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    purchase_type = fields.Selection([
        ('product', 'Goods'),
        ('service', 'Service'),
        ('asset', 'Asset'),
    ], string='Purchase Type', required=True, default='product')
    inventory_status = fields.Selection([
        ('not_received', 'Not Received'),
        ('incomplete', 'Incomplete'),
        ('done', 'Done'),
    ], string='Inventory Status', default='not_received', compute='compute_inventory_status')
    purchase_code = fields.Char(string='Internal order number')
    has_contract = fields.Boolean(string='Hợp đồng khung?')
    has_invoice = fields.Boolean(string='Finance Bill?')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 8), default=1)

    # apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange', compute='_compute_active_manual_currency_rate')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency',
                                                 compute='_compute_active_manual_currency_rate')
    # production_id = fields.Many2many('forlife.production', string='Production Order Code', ondelete='restrict')

    # prod_filter = fields.Boolean(string='Filter Products by Supplier', compute='_compute_')
    # total_discount = fields.Monetary(string='Total Discount', store=True, readonly=True,
    #                                  compute='_amount_all', tracking=True)

    custom_state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('close', 'Close'),
                   ])
    exchange_rate_line = fields.One2many('purchase.order.exchange.rate', 'purchase_order_id', copy=True,
                                         string="Thuế nhập khẩu", compute='_compute_exchange_rate_line_and_cost_line', store=1)
    cost_line = fields.One2many('purchase.order.cost.line', 'purchase_order_id', copy=True, string="Chi phí")
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    location_id = fields.Many2one('stock.location', string="Kho nhận", check_company=True)
    is_inter_company = fields.Boolean(default=False)
    partner_domain = fields.Char()
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True, domain=False,
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    occasion_code_ids = fields.Many2many('occasion.code', string="Case Code")
    account_analytic_ids = fields.Many2many('account.analytic.account', relation='account_analytic_ref',
                                            string="Cost Center")
    is_purchase_request = fields.Boolean(default=False)
    is_check_readonly_partner_id = fields.Boolean()
    is_check_readonly_purchase_type = fields.Boolean()
    source_document = fields.Char(string="Source Document")
    receive_date = fields.Datetime(string='Receive Date')
    note = fields.Char('Note')
    source_location_id = fields.Many2one('stock.location', string="Địa điểm nguồn")
    trade_discount = fields.Integer(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Integer(string='Tổng chiết khấu thương mại')
    count_invoice_inter_company_ncc = fields.Integer(compute='compute_count_invoice_inter_company_ncc')
    count_invoice_inter_fix = fields.Integer(compute='compute_count_invoice_inter_fix')
    count_invoice_inter_company_customer = fields.Integer(compute='compute_count_invoice_inter_company_customer')
    count_delivery_inter_company = fields.Integer(compute='compute_count_delivery_inter_company')
    count_delivery_import_inter_company = fields.Integer(compute='compute_count_delivery_import_inter_company')
    cost_total = fields.Float(string='Tổng chi phí', compute='compute_cost_total')
    is_done_picking = fields.Boolean(default=False, compute='compute_is_done_picking')
    date_order = fields.Datetime('Order Deadline', required=True, states=READONLY_STATES, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")

    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')

    invoice_status_fake = fields.Selection([
        ('no', 'Chưa nhận'),
        ('to invoice', 'Dở dang'),
        ('invoiced', 'Hoàn thành'),
    ], string='Trạng thái hóa đơn', readonly=True, copy=False, default='no')

    rejection_reason = fields.Char(string="Lý do từ chối")
    cancel_reason = fields.Char(string="Lý do huỷ")
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)", compute='compute_origin')
    type_po_cost = fields.Selection([('tax', 'Tax'), ('cost', 'Cost')])
    purchase_synthetic_ids = fields.One2many('forlife.synthetic', 'synthetic_id', compute='_compute_exchange_rate_line_and_cost_line', store=1)

    show_check_availability = fields.Boolean(
        compute='_compute_show_check_availability', invisible=True,
        help='Technical field used to compute whether the button "Check Availability" should be displayed.')

    # Lấy của base về phục vụ import
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Chi tiết',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    payment_term_id = fields.Many2one('account.payment.term', 'Chính sách thanh toán',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")


    def action_view_stock(self):
        for item in self:
            context = {'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('Phiếu xuất khác'),
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('origin', '=', item.name), ('other_export', '=', True)],
                'context': context
            }

    count_stock = fields.Integer(compute="compute_count_stock", copy=False)

    def compute_count_stock(self):
        for item in self:
            item.count_stock = self.env['stock.picking'].search_count([('origin', '=', item.name), ('other_export', '=', True)])

    @api.onchange('partner_id', 'currency_id')
    def onchange_partner_id_warning(self):
        res = super().onchange_partner_id_warning()
        if self.partner_id and self.order_line and self.currency_id:
            for item in self.order_line:
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
        # Do something with res
        return res

    @api.constrains('currency_id')
    def constrains_currency_id(self):
        for item in self:
            if not item.currency_id:
                raise ValidationError('Trường tiền tệ không tồn tại')

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            if self.type_po_cost != 'cost':
                self.exchange_rate = self.currency_id.rate
            else:
                self.exchange_rate = 1

    @api.depends('cost_line', 'cost_line.vnd_amount')
    def compute_cost_total(self):
        for item in self:
            item.cost_total = sum(item.cost_line.mapped('vnd_amount'))

    @api.depends('source_document')
    def compute_origin(self):
        for item in self:
            if item.source_document:
                item.origin = item.source_document
            else:
                item.origin = False

    def compute_inventory_status(self):
        for item in self:
            pk = self.env['stock.picking'].search([('origin', '=', item.name)])
            if pk:
                all_equal_parent_done = all(x == 'done' for x in pk.mapped('state'))
                if all_equal_parent_done:
                    item.inventory_status = 'done'
                else:
                    item.inventory_status = 'incomplete'
            else:
                item.inventory_status = 'not_received'

    def compute_is_done_picking(self):
        for record in self:
            pk = self.env['stock.picking'].search([('origin', '=', record.name)]).mapped('state')
            if pk:
                if 'done' in pk:
                    record.is_done_picking = True
                else:
                    record.is_done_picking = False
            else:
                record.is_done_picking = False

    @api.constrains('order_line')
    def constrains_order_line(self):
        for item in self:
            if not item.order_line:
                raise ValidationError('Bạn chưa nhập sản phẩm')

    @api.constrains('exchange_rate', 'trade_discount')
    def constrains_exchange_rare(self):
        for item in self:
            if item.exchange_rate < 0:
                raise ValidationError('Tỷ giá không được âm!')
            if item.trade_discount < 0:
                raise ValidationError('Chiết khấu thương mại không được âm!')

    # Các action header
    def action_view_invoice_ncc(self):
        for item in self:
            sale_order = self.env['sale.order'].search([('origin', '=', item.name)], limit=1)
            if sale_order:
                ncc = self.data_account_move([('reference', '=', sale_order.name), ('is_from_ncc', '=', True)])
                context = {'create': True, 'delete': True, 'edit': True}
                return {
                    'name': _('Hóa đơn nhà cung cấp'),
                    'view_mode': 'tree,form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', 'in', ncc.ids)],
                    'context': context
                }

    def action_view_invoice_customer(self):
        for item in self:
            customer = self.data_account_move([('reference', '=', item.name), ('is_from_ncc', '=', False)])
            context = {'create': True, 'delete': True, 'edit': True}
            return {
                'name': _('Hóa đơn bán hàng'),
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', customer.ids)],
                'context': context
            }

    def action_view_picking_inter_company(self):
        for item in self:
            context = {'create': True, 'delete': True, 'edit': True}
            so = self.env['sale.order'].search([('origin', '=', item.name)], limit=1)
            if so:
                data = self.env['stock.picking'].search([('origin', '=', so.name)])
                return {
                    'name': _('Phiếu xuất xuất hàng'),
                    'view_mode': 'tree,form',
                    'res_model': 'stock.picking',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', '=', data.ids)],
                    'context': context
                }

    def action_view_import_picking_inter_company(self):
        for item in self:
            context = {'create': True, 'delete': True, 'edit': True}
            data = self.env['stock.picking'].search([('origin', '=', item.name)])
            return {
                'name': _('Phiếu nhập xuất hàng'),
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', data.ids)],
                'context': context
            }

    # Compute field action hearder
    def compute_count_invoice_inter_company_customer(self):
        for item in self:
            data = self.data_account_move([('reference', '=', item.name), ('is_from_ncc', '=', False)])
            if data:
                item.count_invoice_inter_company_customer = len(data)
            else:
                item.count_invoice_inter_company_customer = False

    def data_account_move(self, domain):
        account_move = self.env['account.move'].search(domain)
        return account_move

    def compute_count_delivery_inter_company(self):
        for item in self:
            so = self.env['sale.order'].search([('origin', '=', item.name)], limit=1)
            if so:
                item.count_delivery_inter_company = self.env['stock.picking'].search_count([('origin', '=', so.name)])
            else:
                item.count_delivery_inter_company = False

    def compute_count_delivery_import_inter_company(self):
        for item in self:
            item.count_delivery_import_inter_company = self.env['stock.picking'].search_count(
                [('origin', '=', item.name)])

    def compute_count_invoice_inter_company_ncc(self):
        for item in self:
            so = self.env['sale.order'].search([('origin', '=', item.name)], limit=1)
            if so:
                item.count_invoice_inter_company_ncc = len(self.data_account_move([('reference', '=', so.name), ('is_from_ncc', '=', True)]))
            else:
                item.count_invoice_inter_company_ncc = False

    def compute_count_invoice_inter_fix(self):
        for rec in self:
            picking_in = self.env['stock.picking'].search([('origin', '=', self.name),
                                                           ('state', '=', 'done'),
                                                           ('ware_check', '=', True),
                                                           ('x_is_check_return', '=', False),
                                                           ('picking_type_id.code', '=', 'incoming')
                                                           ])
            rec.count_invoice_inter_fix = self.env['account.move'].search_count(
                [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice')])
            ## check hóa đơn liên quan tới phiếu kho mà bị xóa thì cho phép tạo lại hóa đơn từ pnk đó
            if not rec.count_invoice_inter_fix:
                for line in picking_in:
                    line.ware_check = False

    @api.onchange('trade_discount')
    def onchange_total_trade_discount(self):
        if self.trade_discount:
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_total') / self.trade_discount

    def action_confirm(self):
        for record in self:
            if not record.partner_id:
                raise UserError("Bạn chưa chọn nhà cung cấp!!")
            product_discount_tax = self.env.ref('forlife_purchase.product_discount_tax', raise_if_not_found=False)
            if product_discount_tax and any(line.product_id.id == product_discount_tax.id and line.price_unit > 0 for line in record.order_line):
                raise UserError("Giá CTKM phải = 0. Người dùng vui lòng nhập đơn giá ở phần thông tin tổng chiết khấu thương mại.")
            for orl in record.order_line:
                if orl.price_subtotal <= 0:
                    raise UserError(_('Đơn hàng chứa sản phẩm %s có tổng tiền bằng 0!') % orl.product_id.name)
            record.write({'custom_state': 'confirm'})

    def action_approved(self):
        self.check_purchase_tool_and_equipment()
        for record in self:
            if not record.is_inter_company:
                super(PurchaseOrder, self).button_confirm()
                picking_in = self.env['stock.picking'].search([('origin', '=', record.name)], limit=1)
                picking_in.write({
                    'is_pk_purchase': True
                })
                picking_in.picking_type_id.write({
                    'show_operations': True
                })
                picking_in.write({'state': 'assigned'})
                if picking_in:
                    orl_l_ids = []
                    for orl, pkl in zip(record.order_line, picking_in.move_ids_without_package):
                        if orl.product_id == pkl.product_id:
                            po_l_id = orl.id
                            while po_l_id in orl_l_ids:
                                po_l_id += 1
                            orl_l_ids.append(po_l_id)
                            pkl.write({
                                'po_l_id': po_l_id,
                                'free_good': orl.free_good,
                                'quantity_change': orl.exchange_quantity,
                                'quantity_purchase_done': orl.purchase_quantity,
                                'quantity_done': orl.product_qty,
                                'occasion_code_id': orl.occasion_code_id.id,
                                'work_production': orl.production_id.id,
                            })
                    orl_ids = []
                    for orl, pk in zip(record.order_line, picking_in.move_line_ids_without_package):
                        if orl.product_id == pk.product_id:
                            po_id = orl.id
                            while po_id in orl_ids:
                                po_id += 1
                            orl_ids.append(po_id)
                            pk.write({
                                'po_id': po_id,
                                'purchase_uom': orl.purchase_uom.id,
                                'quantity_change': orl.exchange_quantity,
                                'quantity_purchase_done': orl.product_qty / orl.exchange_quantity if orl.exchange_quantity else False
                            })
                record.write({'custom_state': 'approved'})
            else:
                data = {'partner_id': record.partner_id.id, 'purchase_type': record.purchase_type,
                        'is_purchase_request': record.is_purchase_request,
                        'production_id': record.production_id.id,
                        'event_id': record.event_id,
                        'currency_id': record.currency_id.id,
                        'exchange_rate': record.exchange_rate,
                        'manual_currency_exchange_rate': record.manual_currency_exchange_rate,
                        'company_id': record.company_id.id,
                        'has_contract': record.has_contract,
                        'has_invoice': record.has_invoice,
                        'location_id': record.location_id.id,
                        'source_location_id': record.source_location_id.id,
                        'date_order': record.date_order,
                        'payment_term_id': record.payment_term_id.id,
                        'date_planned': record.date_planned,
                        'receive_date': record.receive_date,
                        'inventory_status': record.inventory_status,
                        'picking_type_id': record.picking_type_id.id,
                        'source_document': record.source_document,
                        'has_contract_commerce': record.has_contract_commerce,
                        'note': record.note,
                        'receipt_reminder_email': record.receipt_reminder_email,
                        'reminder_date_before_receipt': record.reminder_date_before_receipt,
                        'dest_address_id': record.dest_address_id.id,
                        'purchase_order_id': record.id,
                        'name': record.name,
                        }
                order_line = []
                invoice_line_ids = []
                uom = self.env.ref('uom.product_uom_unit').id
                for line in record.order_line:
                    if line.price_subtotal <= 0:
                        raise UserError(
                            'Bạn không thể phê duyệt với đơn mua hàng có thành tiền bằng 0!')
                    product_ncc = self.env['stock.quant'].search(
                        [('location_id', '=', record.source_location_id.id),
                         ('product_id', '=', line.product_id.id)]).mapped('quantity')
                    if sum(product_ncc) < line.product_qty:
                        raise ValidationError('Số lượng sản phẩm (%s) trong kho không đủ.' % (line.product_id.name))
                    data_product = {
                        'product_tmpl_id': line.product_id.product_tmpl_id.id,
                        'product_id': line.product_id.id, 'name': line.product_id.name,
                        'purchase_quantity': line.purchase_quantity,
                        'purchase_uom': line.purchase_uom.id,
                        'exchange_quantity': line.exchange_quantity,
                        'product_quantity': line.product_qty, 'vendor_price': line.vendor_price,
                        'price_unit': line.price_unit,
                        'product_uom': line.product_id.uom_id.id if line.product_id.uom_id else uom,
                        'location_id': line.location_id.id,
                        'taxes_id': line.taxes_id.id, 'price_tax': line.price_tax,
                        'discount_percent': line.discount_percent,
                        'discount': line.discount, 'event_id': line.event_id.id,
                        'production_id': line.production_id.id,
                        'billed': line.billed,
                        'account_analytic_id': line.account_analytic_id.id,
                        'receive_date': line.receive_date,
                        'tolerance': line.tolerance,
                        'price_subtotal': line.price_subtotal
                    }
                    order_line.append(data_product)
                    invoice_line = {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'description': line.product_id.default_code,
                        'request_code': line.request_purchases,
                        'type': line.product_type,
                        'discount': line.discount_percent,
                        'discount_percent': line.discount,
                        'quantity_purchased': line.purchase_quantity,
                        'uom_id': line.product_id.uom_id.id if line.product_id.uom_id else uom,
                        'exchange_quantity': line.exchange_quantity,
                        'quantity': line.product_qty,
                        'vendor_price': line.vendor_price,
                        'price_unit': line.price_unit,
                        'warehouse': line.location_id.id,
                        'taxes_id': line.taxes_id.id,
                        'tax_amount': line.price_tax,
                        'price_subtotal': line.price_subtotal,
                        'account_analytic_id': line.account_analytic_id.id,
                        'work_order': line.production_id.id
                    }
                    invoice_line_ids.append((0, 0, invoice_line))
                self.supplier_sales_order(data, order_line, invoice_line_ids)
                record.write(
                    {'custom_state': 'approved', 'inventory_status': 'incomplete', 'invoice_status_fake': 'no'})

    def check_purchase_tool_and_equipment(self):
        # Kiểm tra xem có phải sp CCDC không (có category đc cấu hình trường tài khoản định giá tồn kho là 153)
        # kiểm tra Đơn Giá mua trên PO + Giá trị chi phí được phân bổ  <> giá trung bình kho của sản phẩm, thì thông báo Hiển thị thông báo cho người dùng: Giá của sản phẩm CCDC này # giá nhập vào đợt trước.Yêu cầu người dùng tạo sản phẩm mới.
        # Nếu Tồn kho = 0 : cho phép nhập giá mới trên line, xác nhận PO và tiến hành nhập kho.
        for rec in self:
            if rec.order_line:
                cost_total = 0
                count_ccdc_product = 0
                if rec.cost_line:
                    cost_total = rec.cost_total
                for line in rec.order_line:
                    if line.product_id.categ_id and line.product_id.categ_id.property_stock_valuation_account_id and line.product_id.categ_id.property_stock_valuation_account_id.code.startswith("153"):
                        count_ccdc_product = count_ccdc_product + line.product_qty
                if count_ccdc_product > 0:
                    product_ccdc_diff_price = []
                    for line in rec.order_line:
                        if line.product_id.categ_id and line.product_id.categ_id.property_stock_valuation_account_id and line.product_id.categ_id.property_stock_valuation_account_id.code.startswith("153"):
                            # kiểm tra tồn kho
                            number_product = self.env['stock.quant'].search(
                                [('location_id', '=', line.location_id.id), ('product_id', '=', line.product_id.id)])
                            if number_product and sum(number_product.mapped('quantity')) > 0:
                                if line.product_id.standard_price != line.price_unit + cost_total / count_ccdc_product:
                                    product_ccdc_diff_price.append(line.product_id.display_name)
                    if product_ccdc_diff_price:
                        raise UserError("Giá sản phẩm công cụ dụng cụ %s khác giá nhập vào đợt trước. Yêu cầu người dùng tạo sản phẩm mới." % ",".join(product_ccdc_diff_price))

    def supplier_sales_order(self, data, order_line, invoice_line_ids):
        company_partner = self.env['res.partner'].search([('internal_code', '=', '3001')], limit=1)
        partner_so = self.env['res.partner'].search([('internal_code', '=', '3000')], limit=1)
        company_id = self.env.company.id
        picking_type_in = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', company_id)], limit=1)
        if company_partner:
            data_all_picking = {}
            order_line_so = []
            for item in order_line:
                key_location = data.get('location_id')
                picking_line = (
                    0, 0,
                    {'product_id': item.get('product_id'), 'name': item.get('name'),
                     'location_dest_id': item.get('location_id'),
                     'location_id': self.env.ref('forlife_stock.export_production_order').id,
                     'product_uom_qty': item.get('product_quantity'), 'price_unit': item.get('price_unit'),
                     'product_uom': item.get('product_uom'), 'reason_id': data.get('location_id'),
                     'quantity_done': item.get('product_quantity')})
                picking_master = {
                    'state': 'done',
                    'picking_type_id': picking_type_in.id,
                    'partner_id': company_partner.id,
                    'location_id': self.env.ref('forlife_stock.export_production_order').id,
                    'location_dest_id': data.get('location_id'),
                    'scheduled_date': datetime.now(),
                    'date_done': data.get('deceive_date'),
                    'move_ids_without_package': [picking_line],
                    'origin': data.get('name'),
                }
                if data_all_picking.get(key_location):
                    data_all_picking.get(key_location).get('move_ids_without_package').append(picking_line)
                else:
                    data_all_picking.update({
                        key_location: picking_master
                    })
                order_line_so.append((
                    0, 0,
                    {'product_id': item.get('product_id'),
                     'name': item.get('name'),
                     'product_uom_qty': item.get('product_quantity'), 'price_unit': item.get('price_unit'),
                     'product_uom': item.get('product_uom'),
                     'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'is_expense': True,
                     'qty_delivered_method': 'analytic',
                     'discount': item.get('discount_percent')}))

            master_so = {
                'company_id': self.source_location_id[0].company_id.id,
                'origin': data.get('name'),
                'partner_id': company_partner.id,
                'payment_term_id': data.get('payment_term_id'),
                'state': 'sent',
                'date_order': data.get('date_order'),
                'warehouse_id': self.source_location_id[0].warehouse_id.id,
                'order_line': order_line_so
            }
            data_so = self.env['sale.order'].sudo().create(master_so)

            # Sử lý phiếu xuất hàng
            st_picking_out = data_so.with_context(
                {'from_inter_company': True, 'company_po': self.source_location_id[0].company_id.id}).action_confirm()
            data_stp_out = self.env['stock.picking'].search([('origin', '=', data_so.name)], limit=1)
            data_stp_out.write({
                'company_id': self.source_location_id[0].company_id.id
            })
            for spl, pol, sol in zip(data_stp_out.move_ids_without_package, order_line, data_so.order_line):
                spl.write({'quantity_done': pol.get('product_quantity'), })
                sol.write({'qty_delivered': spl.quantity_done})
            for item in data_so.picking_ids:
                item.write({
                    'location_id': data.get('source_location_id'),
                    'location_dest_id': data.get('location_id')
                })
            # Sử lý hóa đơn
            invoice_ncc = self.env['sale.advance.payment.inv'].create({
                'sale_order_ids': [(6, 0, data_so.ids)],
                'advance_payment_method': 'delivered',
                'deduct_down_payments': True,
            }).forlife_create_invoices()
            invoice_ncc.invoice_line_ids = None
            invoice_ncc.invoice_line_ids = invoice_line_ids
            invoice_customer = invoice_ncc.copy()
            invoice_ncc.write({
                'purchase_type': data.get('purchase_type'),
                'move_type': 'out_invoice',
                'reference': data_so.name,
                'is_from_ncc': True
            })
            # Vào sổ hóa đơn bán hàng
            invoice_ncc.action_post()
            invoice_customer.write({
                'invoice_date': datetime.now(),
                'move_type': 'in_invoice',
                'reference': data.get('name'),
                'is_from_ncc': False
            })
            sql = f"""update account_move set partner_id = {data.get('partner_id')} where id = {invoice_customer.id}"""
            self._cr.execute(sql)
            # Vào sổ hóa đơn mua hàng
            invoice_customer.action_post()
            data_stp_out.with_context({'skip_immediate': True}).button_validate()
            for st in data_all_picking:
                st_picking_in = self.env['stock.picking'].with_context({'skip_immediate': True}).create(
                    data_all_picking[st]).button_validate()
            return True

        else:
            raise ValidationError('Nhà cung cấp của bạn chưa có đối tác')

    def action_reject(self):
        for record in self:
            record.write({'custom_state': 'reject'})

    def action_cancel(self):
        super(PurchaseOrder, self).button_cancel()
        for record in self:
            record.write({'custom_state': 'cancel'})

    def action_close(self):
        self.write({'custom_state': 'close'})

    @api.model
    def get_import_templates(self):
        if self.env.context.get('default_is_inter_company'):
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/template_liencongtys.xlsx?download=true'
            }]
        elif not self.env.context.get('default_is_inter_company') and self.env.context.get(
                'default_type_po_cost') == 'cost':
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/templatepo_noidias.xlsx?download=true'
            }]
        elif not self.env.context.get('default_is_inter_company') and self.env.context.get(
                'default_type_po_cost') == 'tax':
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/templatepo_thuenhapkhaus.xlsx?download=true'
            }]
        else:
            return True

    @api.depends('company_id', 'currency_id')
    def _compute_active_manual_currency_rate(self):
        for rec in self:
            if rec.company_id or rec.currency_id:
                if rec.company_id.currency_id != rec.currency_id:
                    rec.active_manual_currency_rate = True
                else:
                    rec.active_manual_currency_rate = False
            else:
                rec.active_manual_currency_rate = False

    def write(self, vals):
        old_line_count = len(self.order_line)
        new_line_count = len(vals.get('order_line', []))
        if (new_line_count > old_line_count) and self.custom_state == "approved":
            raise ValidationError('Không thể thêm sản phẩm khi ở trạng thái phê duyệt')
        return super(PurchaseOrder, self).write(vals)

    @api.onchange('company_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.depends('order_line')
    def _compute_exchange_rate_line_and_cost_line(self):
        for rec in self:
            rec.exchange_rate_line = [(5, 0)]
            rec.purchase_synthetic_ids = [(5, 0)]
            for line in rec.order_line:
                exchange_rate_line = self.env['purchase.order.exchange.rate'].create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'vnd_amount': line.total_vnd_amount,
                    'purchase_order_id': rec.id,
                    'qty_product': line.product_qty,
                })
                synthetic_line = self.env['forlife.synthetic'].create({
                    'product_id': line.product_id.id,
                    'description': line.name,
                    'price_unit': line.price_unit,
                    # 'price_subtotal': line.price_subtotal,
                    'quantity': line.product_qty,
                    'before_tax': line.total_value,
                    'discount': line.discount,
                    'synthetic_id': rec.id,
                })
                if exchange_rate_line:
                    exchange_rate_line.update({
                        'vnd_amount': line.total_vnd_amount,
                        'qty_product': line.product_qty,
                    })
                if synthetic_line:
                    synthetic_line.update({
                        'quantity': line.product_qty,
                        'discount': line.discount,
                        'price_unit': line.price_unit,
                        # 'price_subtotal': line.price_subtotal,
                    })

    # def action_update_import(self):
    #     for item in self:
    #         item.exchange_rate_line = [(5, 0)]
    #         for line in item.order_line:
    #             self.env['purchase.order.exchange.rate'].create({
    #                 'product_id': line.product_id.id,
    #                 'name': line.name,
    #                 'usd_amount': line.price_subtotal,
    #                 'purchase_order_id': item.id,
    #                 'qty_product': line.product_qty
    #             })

    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
        # if self.purchase_type and self.order_line:
        #     self.order_line.filtered(lambda s: s.product_type != self.purchase_type).unlink()
        order_line_ids = []
        for line in self.order_line:
            if line.product_type == self.purchase_type:
                order_line_ids.append(line.id)
        self.write({
            'order_line': [(6, 0, order_line_ids)]
        })

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['custom_state'] = 'draft'
        return super().copy(default)

    def action_view_invoice_new(self):
        for rec in self:
            data_search = self.env['account.move'].search(
                [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search), ('move_type', '=', 'in_invoice')],
        }

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        if len(self) > 1 and self[0].type_po_cost in ('cost', 'tax'):
            result = self.create_multi_invoice_vendor()
            move_ids = [move.id for move in result]
            return {
                'name': 'Hóa đơn nhà cung cấp',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_id': False,
                'view_mode': 'tree,form',
                'domain': [('id', 'in', move_ids)],
            }
        else:
            if self.purchase_type in ('service', 'asset'):
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                # 1) Prepare invoice vals and clean-up the section lines
                invoice_vals_list = []
                sequence = 10
                for order in self:
                    order.write({
                        'invoice_status_fake': 'to invoice',
                    })
                    if order.custom_state != 'approved':
                        raise UserError(
                            _('Tạo hóa đơn không hợp lệ!'))
                    order = order.with_company(order.company_id)
                    pending_section = None
                    # Invoice values.
                    invoice_vals = order._prepare_invoice()
                    invoice_vals.update({'purchase_type': order.purchase_type, 'invoice_date': datetime.now(),
                                         'exchange_rate': order.exchange_rate, 'currency_id': order.currency_id.id})
                    # Invoice line values (keep only necessary sections).
                    invoi_relationship = self.env['account.move'].search([('reference', '=', order.name),
                                                                          ('partner_id', '=', order.partner_id.id)])
                    if invoi_relationship:
                        if sum(invoi_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(order.order_line.mapped('price_subtotal')):
                            raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng!'))
                        else:
                            for line in order.order_line:
                                wave = invoi_relationship.invoice_line_ids.filtered(lambda w: str(w.po_id) == str(line.id) and w.product_id.id == line.product_id.id)
                                quantity = 0
                                for nine in wave:
                                    quantity += nine.quantity
                                    data_line = {
                                        'po_id': line.id,
                                        'product_id': line.product_id.id,
                                        'sequence': sequence,
                                        'promotions': line.free_good,
                                        'exchange_quantity': line.exchange_quantity,
                                        'quantity': line.product_qty - quantity,
                                        'vendor_price': line.vendor_price,
                                        'warehouse': line.location_id.id,
                                        'discount': line.discount_percent,
                                        'event_id': line.event_id.id,
                                        'work_order': line.production_id.id,
                                        'account_analytic_id': line.account_analytic_id.id,
                                        'request_code': line.request_purchases,
                                        'quantity_purchased': line.purchase_quantity - nine.quantity_purchased,
                                        'discount_percent': line.discount,
                                        'taxes_id': line.taxes_id.id,
                                        'tax_amount': line.price_tax,
                                        'uom_id': line.product_uom.id,
                                        'price_unit': line.price_unit,
                                        'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                                    }
                                    if line.display_type == 'line_section':
                                        pending_section = line
                                        continue
                                    if pending_section:
                                        line_vals = pending_section._prepare_account_move_line()
                                        line_vals.update(data_line)
                                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                        sequence += 1
                                        pending_section = None
                                    line_vals = line._prepare_account_move_line()
                                    line_vals.update(data_line)
                                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                    sequence += 1
                    else:
                        for line in order.order_line:
                            data_line = {
                                'po_id': line.id,
                                'product_id': line.product_id.id,
                                'sequence': sequence,
                                'price_subtotal': line.price_subtotal,
                                'promotions': line.free_good,
                                'exchange_quantity': line.exchange_quantity,
                                'quantity': line.product_qty,
                                'vendor_price': line.vendor_price,
                                'warehouse': line.location_id.id,
                                'discount': line.discount_percent,
                                'event_id': line.event_id.id,
                                'work_order': line.production_id.id,
                                'account_analytic_id': line.account_analytic_id.id,
                                'request_code': line.request_purchases,
                                'quantity_purchased': line.purchase_quantity,
                                'discount_percent': line.discount,
                                'taxes_id': line.taxes_id.id,
                                'tax_amount': line.price_tax,
                                'uom_id': line.product_uom.id,
                                'price_unit': line.price_unit,
                                'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                            }
                            if line.display_type == 'line_section':
                                pending_section = line
                                continue
                            if pending_section:
                                line_vals = pending_section._prepare_account_move_line()
                                line_vals.update(data_line)
                                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                sequence += 1
                                pending_section = None
                            line_vals = line._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            sequence += 1
                        # invoice_vals_list.append(invoice_vals)
                    invoice_vals_list.append(invoice_vals)
                # 2) group by (company_id, partner_id, currency_id) for batch creation
                new_invoice_vals_list = []
                for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                        x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                    origins = set()
                    payment_refs = set()
                    refs = set()
                    ref_invoice_vals = None
                    for invoice_vals in invoices:
                        if not ref_invoice_vals:
                            ref_invoice_vals = invoice_vals
                        else:
                            ref_invoice_vals['invoice_line_ids'] = invoice_vals['invoice_line_ids']
                        origins.add(invoice_vals['invoice_origin'])
                        payment_refs.add(invoice_vals['payment_reference'])
                        refs.add(invoice_vals['ref'])
                    ref_invoice_vals.update({
                        'purchase_type': self.purchase_type if len(self) == 1 else 'product',
                        'reference': ', '.join(self.mapped('name')),
                        'ref': ', '.join(refs)[:2000],
                        'invoice_origin': ', '.join(origins),
                        'is_check': True,
                        'purchase_order_product_id': [(6, 0, [self.id])],
                        'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                    })
                    new_invoice_vals_list.append(ref_invoice_vals)
                invoice_vals_list = new_invoice_vals_list
            else:
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                # 1) Prepare invoice vals and clean-up the section lines
                invoice_vals_list = []
                sequence = 10
                picking_in = self.env['stock.picking'].search([('origin', '=', self.name),
                                                               ('state', '=', 'done'),
                                                               ('ware_check', '=', False),
                                                               ('x_is_check_return', '=', False),
                                                               ('picking_type_id.code', '=', 'incoming')
                                                               ])
                picking_in_return = self.env['stock.picking'].search([('origin', '=', self.name),
                                                                      ('state', '=', 'done'),
                                                                      ('ware_check', '=', False),
                                                                      ('picking_type_id.code', '=', 'incoming'),
                                                                      ('x_is_check_return', '=', True)
                                                                      ])
                # ('x_is_check_return', '=', False)
                for order in self:
                    if order.custom_state != 'approved':
                        raise UserError(_('Tạo hóa đơn không hợp lệ!'))
                    order = order.with_company(order.company_id)
                    pending_section = None
                    # Invoice values.
                    invoice_vals = order._prepare_invoice()
                    invoice_vals.update({'purchase_type': order.purchase_type, 'invoice_date': datetime.now(),
                                         'exchange_rate': order.exchange_rate, 'currency_id': order.currency_id.id})
                    # Invoice line values (keep only necessary sections).
                    for line in order.order_line:
                        wave = picking_in.move_line_ids_without_package.filtered(lambda w: str(w.po_id) == str(line.id)
                                                                                 and w.product_id.id == line.product_id.id
                                                                                 and w.picking_type_id.code == 'incoming'
                                                                                 and w.picking_id.x_is_check_return == False)
                        if picking_in:
                            for wave_item in wave:
                                purchase_return = picking_in_return.move_line_ids_without_package.filtered(
                                    lambda r: str(r.po_id) == str(wave_item.po_id)
                                    and r.product_id.id == wave_item.product_id.id
                                    and r.picking_id.relation_return == wave_item.picking_id.name
                                    and r.picking_id.x_is_check_return == True)
                                if purchase_return:
                                    for x_return in purchase_return:
                                        if wave_item.picking_id.name == x_return.picking_id.relation_return:
                                            data_line = {
                                                'ware_name': wave_item.picking_id.name,
                                                'po_id': line.id,
                                                'product_id': line.product_id.id,
                                                'sequence': sequence,
                                                'price_subtotal': line.price_subtotal,
                                                'promotions': line.free_good,
                                                'exchange_quantity': wave_item.quantity_change - x_return.quantity_change,
                                                'quantity': wave_item.qty_done - x_return.qty_done,
                                                'vendor_price': line.vendor_price,
                                                'warehouse': line.location_id.id,
                                                'discount': line.discount_percent,
                                                'event_id': line.event_id.id,
                                                'work_order': line.production_id.id,
                                                'account_analytic_id': line.account_analytic_id.id,
                                                'request_code': line.request_purchases,
                                                'quantity_purchased': wave_item.quantity_purchase_done - x_return.quantity_purchase_done,
                                                'discount_percent': line.discount,
                                                'taxes_id': line.taxes_id.id,
                                                'tax_amount': line.price_tax,
                                                'uom_id': line.product_uom.id,
                                                'price_unit': line.price_unit,
                                                'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                                            }
                                            if line.display_type == 'line_section':
                                                pending_section = line
                                                continue
                                            if pending_section:
                                                line_vals = pending_section._prepare_account_move_line()
                                                line_vals.update(data_line)
                                                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                                sequence += 1
                                                pending_section = None
                                            x_return.picking_id.ware_check = True
                                            wave.picking_id.ware_check = True
                                            line_vals = line._prepare_account_move_line()
                                            line_vals.update(data_line)
                                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                            sequence += 1
                                else:
                                    data_line = {
                                        'ware_name': wave_item.picking_id.name,
                                        'po_id': line.id,
                                        'product_id': line.product_id.id,
                                        'sequence': sequence,
                                        'price_subtotal': line.price_subtotal,
                                        'promotions': line.free_good,
                                        'exchange_quantity': wave_item.quantity_change,
                                        'quantity': wave_item.qty_done,
                                        'vendor_price': line.vendor_price,
                                        'warehouse': line.location_id.id,
                                        'discount': line.discount_percent,
                                        'event_id': line.event_id.id,
                                        'work_order': line.production_id.id,
                                        'account_analytic_id': line.account_analytic_id.id,
                                        'request_code': line.request_purchases,
                                        'quantity_purchased': wave_item.quantity_purchase_done,
                                        'discount_percent': line.discount,
                                        'taxes_id': line.taxes_id.id,
                                        'tax_amount': line.price_tax,
                                        'uom_id': line.product_uom.id,
                                        'price_unit': line.price_unit,
                                        'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                                    }
                                    if line.display_type == 'line_section':
                                        pending_section = line
                                        continue
                                    if pending_section:
                                        line_vals = pending_section._prepare_account_move_line()
                                        line_vals.update(data_line)
                                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                        sequence += 1
                                        pending_section = None
                                    wave.picking_id.ware_check = True
                                    line_vals = line._prepare_account_move_line()
                                    line_vals.update(data_line)
                                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                    sequence += 1
                                invoice_vals_list.append(invoice_vals)
                        else:
                            raise UserError(_('Đơn mua đã có hóa đơn liên quan tương ứng với phiếu nhập kho!'))
                # 2) group by (company_id, partner_id, currency_id) for batch creation
                new_invoice_vals_list = []
                picking_incoming = picking_in.filtered(lambda r: r.origin == order.name
                                                       and r.state == 'done'
                                                       and r.picking_type_id.code == 'incoming'
                                                       and r.ware_check == True
                                                       and r.x_is_check_return == False)
                for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                        x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                    origins = set()
                    payment_refs = set()
                    refs = set()
                    ref_invoice_vals = None
                    for invoice_vals in invoices:
                        if not ref_invoice_vals:
                            ref_invoice_vals = invoice_vals
                        else:
                            ref_invoice_vals['invoice_line_ids'] = invoice_vals['invoice_line_ids']
                        origins.add(invoice_vals['invoice_origin'])
                        payment_refs.add(invoice_vals['payment_reference'])
                        refs.add(invoice_vals['ref'])
                    ref_invoice_vals.update({
                        'purchase_type': self.purchase_type if len(self) == 1 else 'product',
                        'reference': ', '.join(self.mapped('name')),
                        'ref': ', '.join(refs)[:2000],
                        'invoice_origin': ', '.join(origins),
                        # 'is_check': True,
                        'type_inv': self.type_po_cost,
                        'move_type': 'in_invoice',
                        'purchase_order_product_id': [(6, 0, [self.id])],
                        'receiving_warehouse_id': [(6, 0, picking_incoming.ids)],
                        'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') or self.type_po_cost else False,
                        'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                    })
                    new_invoice_vals_list.append(ref_invoice_vals)
                invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)
            for line in moves.invoice_line_ids:
                if line.product_id:
                    if line.product_id.property_account_expense_id:
                        account_id = line.product_id.property_account_expense_id.id
                    else:
                        account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                    line.account_id = account_id
            # 3.1) ẩn nút trả hàng khi hóa đơn của pnk đã tồn tại
            # if moves:
            #     for item in moves:
            #         if item.state == 'posted':
            #             picking_in_return = self.env['stock.picking'].search([('origin', '=', self.name),
            #                                                                   ('x_is_check_return', '=', True)
            #                                                                   ])
            #             for nine in item.receiving_warehouse_id:
            #                 nine.x_hide_return = True
            #             for line in picking_in_return:
            #                 line.x_hide_return = True

            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(
                lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
            return {
                'name': 'Hóa đơn nhà cung cấp',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_id': False,
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves.ids), ('move_type', '=', 'in_invoice')],
            }

    def create_multi_invoice_vendor(self):
        sequence = 10
        vals_all_invoice = {}
        for order in self:
            if order.purchase_type in ('service', 'asset'):
                if order.custom_state != 'approved':
                    raise UserError(_('Tạo hóa đơn không hợp lệ cho đơn mua %s!') % order.name)
                invoi_relationship = self.env['account.move'].search([('reference', '=', order.name),
                                                                      ('partner_id', '=', order.partner_id.id)])
                if invoi_relationship:
                    if sum(invoi_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(
                            order.order_line.mapped('price_subtotal')):
                        raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng %s!') % order.name)
                    else:
                        for line in order.order_line:
                            quantity = 0
                            wave = invoi_relationship.invoice_line_ids.filtered(lambda w: str(w.po_id) == str(line.id) and w.product_id.id == line.product_id.id)
                            for nine in wave:
                                quantity += nine.quantity
                                data_line = {
                                    'po_id': line.id,
                                    'product_id': line.product_id.id,
                                    'sequence': sequence,
                                    'promotions': line.free_good,
                                    'exchange_quantity': line.exchange_quantity,
                                    'quantity': line.product_qty - quantity,
                                    'vendor_price': line.vendor_price,
                                    'warehouse': line.location_id.id,
                                    'discount': line.discount_percent,
                                    'event_id': line.event_id.id,
                                    'work_order': line.production_id.id,
                                    'account_analytic_id': line.account_analytic_id.id,
                                    'request_code': line.request_purchases,
                                    'quantity_purchased': line.purchase_quantity - nine.quantity_purchased,
                                    'discount_percent': line.discount,
                                    'taxes_id': line.taxes_id.id,
                                    'tax_amount': line.price_tax,
                                    'uom_id': line.product_uom.id,
                                    'price_unit': line.price_unit,
                                    'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                                }
                            sequence += 1
                            key = order.purchase_type, order.partner_id.id, order.company_id.id
                            invoice_vals = order._prepare_invoice()
                            invoice_vals.update({'purchase_type': order.purchase_type,
                                                 'invoice_date': datetime.now(),
                                                 'exchange_rate': order.exchange_rate,
                                                 'currency_id': order.currency_id.id,
                                                 'reference': order.name,
                                                 })
                            order = order.with_company(order.company_id)
                            line_vals = line._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            if vals_all_invoice.get(key):
                                vals_all_invoice.get(key)['invoice_line_ids'].append((0, 0, line_vals))
                            else:
                                vals_all_invoice.update({
                                    key: invoice_vals
                                })
                else:
                    for line in order.order_line:
                        data_line = {
                            'po_id': line.id,
                            'product_id': line.product_id.id,
                            'sequence': sequence,
                            'price_subtotal': line.price_subtotal,
                            'promotions': line.free_good,
                            'exchange_quantity': line.exchange_quantity,
                            'quantity': line.product_qty,
                            'vendor_price': line.vendor_price,
                            'warehouse': line.location_id.id,
                            'discount': line.discount_percent,
                            'event_id': line.event_id.id,
                            'work_order': line.production_id.id,
                            'account_analytic_id': line.account_analytic_id.id,
                            'request_code': line.request_purchases,
                            'quantity_purchased': line.purchase_quantity,
                            'discount_percent': line.discount,
                            'taxes_id': line.taxes_id.id,
                            'tax_amount': line.price_tax,
                            'uom_id': line.product_uom.id,
                            'price_unit': line.price_unit,
                            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                        }
                        sequence += 1
                        key = order.purchase_type, order.partner_id.id, order.company_id.id
                        invoice_vals = order._prepare_invoice()
                        invoice_vals.update({'purchase_type': order.purchase_type,
                                             'invoice_date': datetime.now(),
                                             'exchange_rate': order.exchange_rate,
                                             'currency_id': order.currency_id.id,
                                             'reference': order.name,
                                             })
                        order = order.with_company(order.company_id)
                        line_vals = line._prepare_account_move_line()
                        line_vals.update(data_line)
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        if vals_all_invoice.get(key):
                            vals_all_invoice.get(key)['invoice_line_ids'].append((0, 0, line_vals))
                        else:
                            vals_all_invoice.update({
                            key: invoice_vals
                        })
            else:
                # if order.inventory_status != 'done' and order.purchase_type == 'product':
                #     raise ValidationError(
                #         'Phiếu nhận hàng của đơn mua hàng %s có thể chưa hoàn thành/chưa có!' % (order.name))
                if order.custom_state != 'approved':
                    raise UserError(
                        _('Tạo hóa đơn không hợp lệ!'))
                picking_in = self.env['stock.picking'].search([('origin', '=', order.name),
                                                               ('state', '=', 'done'),
                                                               ('ware_check', '=', False),
                                                               ('x_is_check_return', '=', False),
                                                               ('picking_type_id.code', '=', 'incoming')
                                                               ])
                for line in order.order_line:
                    wave = picking_in.move_line_ids_without_package.filtered(lambda w: str(w.po_id) == str(line.id)
                                                                                       and w.product_id.id == line.product_id.id
                                                                                       and w.picking_type_id.code == 'incoming'
                                                                                       and w.picking_id.x_is_check_return == False)
                    if wave:
                        for wave_item in wave:
                            data_line = {
                                'ware_name': wave_item.picking_id.name,
                                'po_id': line.id,
                                'product_id': line.product_id.id,
                                'sequence': sequence,
                                'price_subtotal': line.price_subtotal,
                                'promotions': line.free_good,
                                'exchange_quantity': wave_item.quantity_change,
                                'quantity': wave_item.qty_done,
                                'vendor_price': line.vendor_price,
                                'warehouse': line.location_id.id,
                                'discount': line.discount_percent,
                                'event_id': line.event_id.id,
                                'work_order': line.production_id.id,
                                'account_analytic_id': line.account_analytic_id.id,
                                'request_code': line.request_purchases,
                                'quantity_purchased': wave_item.quantity_purchase_done,
                                'discount_percent': line.discount,
                                'taxes_id': line.taxes_id.id,
                                'tax_amount': line.price_tax,
                                'uom_id': line.product_uom.id,
                                'price_unit': line.price_unit,
                                'total_vnd_amount': line.price_subtotal * order.exchange_rate,
                            }
                            wave.picking_id.ware_check = True
                    else:
                        raise UserError(_('Đơn mua có mã phiếu là %s đã có hóa đơn liên quan tương ứng với phiếu nhập kho!') % order.name)
                    sequence += 1
                    key = order.purchase_type, order.partner_id.id, order.company_id.id
                    invoice_vals = order._prepare_invoice()
                    picking_incoming = picking_in.filtered(lambda r: r.origin == order.name
                                                                     and r.state == 'done'
                                                                     and r.picking_type_id.code == 'incoming'
                                                                     and r.ware_check == True
                                                                     and r.x_is_check_return == False)
                    invoice_vals.update({'purchase_type': order.purchase_type,
                                         'invoice_date': datetime.now(),
                                         'exchange_rate': order.exchange_rate,
                                         'currency_id': order.currency_id.id,
                                         'reference': order.name,
                                         'receiving_warehouse_id': [(6, 0, picking_incoming.ids)],
                                         })
                    order = order.with_company(order.company_id)
                    line_vals = line._prepare_account_move_line()
                    line_vals.update(data_line)
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    if vals_all_invoice.get(key):
                        vals_all_invoice.get(key)['invoice_line_ids'].append((0, 0, line_vals))
                    else:
                        vals_all_invoice.update({
                            key: invoice_vals
                        })

        moves = self.env['account.move'].with_context(default_move_type='in_invoice')
        created_moves = []
        for data in vals_all_invoice:
            move = moves.create(vals_all_invoice.get(data))
            if move:
                for line in move.invoice_line_ids:
                    if line.product_id:
                        account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                        line.account_id = account_id
                for line in move:
                    reference = []
                    for nine in line.purchase_order_product_id:
                        reference.append(nine.name)
                        ref_join = ', '.join(reference)
                        line.reference = ref_join
            move.filtered(
                lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
            created_moves.append(move)
        return created_moves

    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        location_ids = self.order_line.mapped('location_id')
        if self.location_id:
            location_ids |= self.location_id
        if not location_ids:
            return {
                'picking_type_id': self.picking_type_id.id,
                'partner_id': self.partner_id.id,
                'user_id': False,
                'date': self.date_order,
                'origin': self.name,
                'location_dest_id': self._get_destination_location(),
                'location_id': self.partner_id.property_stock_supplier.id,
                'company_id': self.company_id.id,
            }
        vals = []
        for location in location_ids:
            vals.append({
                'picking_type_id': self.picking_type_id.id,
                'partner_id': self.partner_id.id,
                'user_id': False,
                'date': self.date_order,
                'origin': self.name,
                'location_dest_id': location.id,
                'location_id': self.partner_id.property_stock_supplier.id,
                'company_id': self.company_id.id,
            })
        return vals

    def _prepare_invoice(self):
        values = super(PurchaseOrder, self)._prepare_invoice()
        values.update({
            'trade_discount': self.trade_discount,
            'total_trade_discount': self.total_trade_discount
        })
        return values


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'free_good', 'discount', 'discount_percent')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']
            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    price_unit = fields.Float(string='Đơn giá', required=True, digits='Product Price', compute='compute_price_unit',
                              store=1)
    product_qty = fields.Float(string='Quantity', digits=(16, 0), required=True,
                               compute='_compute_product_qty', store=True, readonly=False)
    asset_code = fields.Many2one('assets.assets', string='Asset code')
    asset_name = fields.Char(string='Asset name')
    purchase_quantity = fields.Float('Purchase Quantity', digits='Product Unit of Measure')
    purchase_uom = fields.Many2one('uom.uom', string='Purchase UOM')
    exchange_quantity = fields.Float('Exchange Quantity')
    # line_sub_total = fields.Monetary(compute='_get_line_subtotal', string='Line Subtotal', readonly=True, store=True)
    discount_percent = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    discount = fields.Float(string='Discount (Amount)', digits='Discount', default=0.0)
    free_good = fields.Boolean(string='Free Goods')
    warehouses_id = fields.Many2one('stock.warehouse', string="Whs", check_company=True)
    location_id = fields.Many2one('stock.location', string="Địa điểm kho", check_company=True)
    production_id = fields.Many2one('forlife.production', string='Production Order Code')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Account Analytic Account')
    request_line_id = fields.Many2one('purchase.request', string='Phiếu yêu cầu')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    vendor_price = fields.Float(string='Vendor Price', compute='compute_vendor_price_ncc', store=1)
    readonly_discount = fields.Boolean(default=False)
    readonly_discount_percent = fields.Boolean(default=False)
    request_purchases = fields.Char(string='Purchases', readonly=1)
    is_passersby = fields.Boolean(related='order_id.is_passersby')
    supplier_id = fields.Many2one('res.partner', related='order_id.partner_id')
    receive_date = fields.Datetime(string='Date receive')
    tolerance = fields.Float(related='product_id.tolerance', string='Dung sai')
    billed = fields.Float(string='Đã có hóa đơn', compute='compute_billed')
    received = fields.Integer(string='Đã nhận', compute='compute_received')
    occasion_code_id = fields.Many2one('occasion.code', string="Mã vụ việc")
    description = fields.Char('Mô tả', related='product_id.name')
    # Phục vụ import
    taxes_id = fields.Many2many('account.tax', string='Thuế(%)',
                                domain=['|', ('active', '=', False), ('active', '=', True)])
    domain_uom = fields.Char(string='Lọc đơn vị', compute='compute_domain_uom')
    is_red_color = fields.Boolean(compute='compute_vendor_price_ncc')
    name = fields.Char(related='product_id.name', store=True, required=False)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', store=True, required=False)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    is_change_vendor = fields.Integer()

    total_vnd_amount = fields.Float('Tổng tiền VNĐ', compute='_compute_total_vnd_amount', store=1)
    total_value = fields.Float()

    @api.depends('price_subtotal', 'order_id.exchange_rate', 'order_id')
    def _compute_total_vnd_amount(self):
        for rec in self:
            rec.total_vnd_amount = (rec.price_subtotal * rec.order_id.exchange_rate)

    @api.depends('price_subtotal', 'order_id.exchange_rate', 'order_id')
    def _compute_total_vnd_amount(self):
        for rec in self:
            rec.total_vnd_amount = (rec.price_subtotal * rec.order_id.exchange_rate)

    @api.onchange('product_id', 'is_change_vendor')
    def onchange_product_id(self):
        if self.product_id and self.currency_id:
            self.product_uom = self.product_id.uom_id.id
            date_item = datetime.now().date()
            supplier_info = self.search_product_sup(
                [('product_id', '=', self.product_id.id), ('partner_id', '=', self.supplier_id.id),
                 ('date_start', '<', date_item),
                 ('date_end', '>', date_item),
                 ('currency_id', '=', self.currency_id.id)
                 ])
            if supplier_info:
                self.purchase_uom = supplier_info[-1].product_uom

    @api.depends('supplier_id', 'product_id', )
    def compute_domain_uom(self):
        for item in self:
            date_item = datetime.now().date()
            supplier_info = self.search_product_sup(
                [('product_id', '=', item.product_id.id), ('partner_id', '=', item.supplier_id.id),
                 ('currency_id', '=', item.currency_id.id),
                 ('date_start', '<', date_item),
                 ('date_end', '>',
                  date_item)]) if item.supplier_id and item.product_id and item.currency_id else None
            item.domain_uom = json.dumps(
                [('id', 'in', supplier_info.mapped('product_uom').ids)]) if supplier_info else json.dumps([])

    def search_product_sup(self, domain):
        supplier_info = self.env['product.supplierinfo'].search(domain)
        return supplier_info

    @api.constrains('asset_code')
    def constrains_asset_code(self):
        for item in self:
            if item.order_id.purchase_type == 'asset':
                if item.asset_code and item.asset_code.asset_account.code and item.product_id and item.product_id.categ_id and item.product_id.categ_id.with_company(item.company_id).property_valuation == 'real_time' and item.product_id.categ_id.with_company(item.company_id).property_stock_valuation_account_id:
                    if item.asset_code.asset_account.code != item.product_id.categ_id.with_company(item.company_id).property_stock_valuation_account_id.code:
                        raise ValidationError(
                            'Mã tài sản của bạn khác với mã loại cọc trong tài khoản định giá tồn kho thuộc nhóm sản phẩm')
                else:
                    raise ValidationError(
                        'Bạn chưa cấu hình nhóm sản phẩm hay tài khoản định giá tồn kho cho sản phẩm %s' % (
                            item.product_id.name))

    @api.constrains('taxes_id')
    def constrains_taxes_id(self):
        for item in self:
            if len(item.taxes_id) > 1:
                raise ValidationError('Bạn chỉ chọn được 1 giá trị thuế')

    _sql_constraints = [
        (
            "discount_limit",
            "CHECK (discount_percent <= 100.0)",
            "Discount Pervent must be lower than 100%.",
        )
    ]

    def compute_received(self):
        for item in self:
            if item.order_id:
                st_picking = self.env['stock.picking'].search(
                    [('origin', '=', item.order_id.name), ('state', '=', 'done')])
                if st_picking:
                    acc_move_line = self.env['stock.move'].search(
                        [('picking_id', 'in', st_picking.ids), ('product_id', '=', item.product_id.id)]).mapped(
                        'quantity_done')
                    if item.qty_returned:
                        item.received = sum(acc_move_line) - item.qty_returned
                    else:
                        item.received = sum(acc_move_line)
                else:
                    item.received = False
            else:
                item.received = False

    def compute_billed(self):
        for item in self:
            if item.order_id:
                acc_move = self.env['account.move'].search(
                    [('reference', '=', item.order_id.name), ('state', '=', 'posted')])
                if acc_move:
                    acc_move_line = self.env['account.move.line'].search(
                        [('move_id', 'in', acc_move.ids), ('product_id', '=', item.product_id.id)]).mapped('quantity')
                    item.billed = sum(acc_move_line)
                else:
                    item.billed = False
            else:
                item.billed = False

    @api.depends('exchange_quantity', 'purchase_quantity', 'product_id', 'purchase_uom',
                 'order_id.partner_id', 'order_id.partner_id.is_passersby', 'order_id', 'order_id.currency_id')
    def compute_vendor_price_ncc(self):
        today = datetime.now().date()
        for rec in self:
            if not (rec.product_id and rec.order_id.partner_id and rec.purchase_uom and rec.order_id.currency_id):
                rec.is_red_color = False
                continue
            data = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id),
                ('partner_id', '=', rec.order_id.partner_id.id),
                ('currency_id', '=', rec.order_id.currency_id.id),
                ('amount_conversion', '=', rec.exchange_quantity),
                ('date_start', '<=', today),
                ('date_end', '>=', today)
            ])
            rec.is_red_color = True if rec.exchange_quantity not in data.mapped(
                'amount_conversion') else False
            if rec.product_id and rec.order_id.partner_id and rec.purchase_uom and rec.order_id.currency_id and not rec.is_red_color and not rec.order_id.partner_id.is_passersby:
                for line in data:
                    if line.product_uom.id == rec.purchase_uom.id:
                        rec.vendor_price = line.price if line else False
                        rec.exchange_quantity = line.amount_conversion
                    else:
                        if rec.purchase_quantity > max(data.mapped('min_qty')):
                            closest_quantity = max(data.mapped('min_qty'))
                            if closest_quantity == line.min_qty:
                                rec.vendor_price = line.price
                                rec.exchange_quantity = line.amount_conversion
                        else:
                            closest_quantity = min(data.mapped('min_qty'), key=lambda x: abs(x - rec.purchase_quantity))
                            if closest_quantity == line.min_qty:
                                rec.vendor_price = line.price
                                rec.exchange_quantity = line.amount_conversion

    @api.depends('vendor_price', 'exchange_quantity')
    def compute_price_unit(self):
        for rec in self:
            rec.price_unit = rec.vendor_price / rec.exchange_quantity if rec.exchange_quantity else False

    @api.onchange('free_good')
    def onchange_vendor_prices(self):
        if self.free_good:
            self.vendor_price = False

    @api.onchange('product_id', 'order_id', 'order_id.receive_date', 'order_id.location_id', 'order_id.production_id',
                  'order_id.account_analytic_ids', 'order_id.occasion_code_ids', 'order_id.event_id')
    def onchange_receive_date(self):
        if self.order_id:
            self.receive_date = self.order_id.receive_date
            self.location_id = self.order_id.location_id
            self.production_id = self.order_id.production_id
            if self.order_id.account_analytic_ids:
                self.account_analytic_id = self.order_id.account_analytic_ids[-1].id.origin
            self.event_id = self.order_id.event_id
            if self.order_id.occasion_code_ids:
                self.occasion_code_id = self.order_id.occasion_code_ids[-1].id.origin

    @api.onchange('product_id', 'order_id', 'order_id.location_id')
    def onchange_location_id(self):
        if self.order_id and self.order_id.location_id:
            self.location_id = self.order_id.location_id

    # discount
    @api.onchange("free_good")
    def _onchange_free_good(self):
        if self.free_good:
            self.discount = self.discount_percent = False
            self.readonly_discount_percent = self.readonly_discount = True
        else:
            self.readonly_discount_percent = self.readonly_discount = False

    @api.onchange("discount_percent")
    def _onchange_discount_percent(self):
        if not self.readonly_discount_percent:
            if self.discount_percent:
                self.discount = self.discount_percent * self.price_unit * self.product_qty * 0.01
                self.readonly_discount = True
            else:
                self.readonly_discount = False

    @api.onchange("discount")
    def _onchange_discount(self):
        if not self.readonly_discount:
            if self.discount and self.price_unit > 0 and self.product_qty > 0:
                self.discount_percent = self.discount / (self.price_unit * self.product_qty * 0.01)
                self.readonly_discount_percent = True
            else:
                self.readonly_discount_percent = False

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            discount=self.discount_percent,
            price_subtotal=self.price_subtotal,
        )

    def _get_discounted_price_unit(self):
        self.ensure_one()
        if self.discount:
            return self.price_unit - self.discount
        else:
            return self.price_unit * (1 - self.discount_percent / 100)
        return self.price_unit

    def write(self, vals):
        res = super().write(vals)
        if "discount" in vals or "price_unit" in vals or "discount_percent" in vals:
            for line in self.filtered(lambda l: l.order_id.state == "purchase"):
                # Avoid updating kit components' stock.move
                moves = line.move_ids.filtered(
                    lambda s: s.state not in ("cancel", "done")
                    and s.product_id == line.product_id
                )
                moves.write({"price_unit": line._get_discounted_price_unit()})
        return res

    # exchange rate
    @api.depends('purchase_quantity', 'purchase_uom', 'product_qty', 'product_uom')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines:
                continue
            params = {'order_id': line.order_id}
            uom_id = line.purchase_uom if line.product_id.detailed_type == 'product' else line.product_uom
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=uom_id,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not seller:
                if line.product_id.detailed_type == 'product':
                    continue
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                po_line_uom = line.product_uom or line.product_id.uom_po_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.taxes_id,
                    line.company_id,
                )
                price_unit = line.product_id.currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order,
                    False
                )
                line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                               self.env[
                                                                                   'decimal.precision'].precision_get(
                                                                                   'Product Price')))
                continue

            price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                 line.product_id.supplier_taxes_id,
                                                                                 line.taxes_id,
                                                                                 line.company_id) if seller else 0.0
            price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order)

            # if line.product_id.detailed_type == 'product':
            #     line.vendor_price = seller.product_uom._compute_price(price_unit, line.product_uom)
            #     line.price_unit = line.vendor_price / line.exchange_quantity if line.exchange_quantity else 0.0
            # else:
            #     line.price_unit = seller.product_uom._compute_0price(price_unit, line.product_uom)

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

    @api.depends('purchase_quantity', 'exchange_quantity')
    def _compute_product_qty(self):
        for line in self:
            if line.purchase_quantity and line.exchange_quantity:
                line.product_qty = line.purchase_quantity * line.exchange_quantity
            else:
                line.product_qty = line.purchase_quantity

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids \
            .filtered(lambda r: r.partner_id == self.order_id.partner_id and (
                not r.product_id or r.product_id == self.product_id)) \
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
        else:
            self.product_qty = 1.0
        # re-write thông tin purchase_uom,product_uom
        self.product_uom = self.product_id.uom_id.id

    @api.constrains('exchange_quantity', 'purchase_quantity')
    def _constrains_exchange_quantity_and_purchase_quantity(self):
        for rec in self:
            if rec.exchange_quantity < 0:
                raise ValidationError(_('The number of exchanges is not filled with negative numbers !!'))
            elif rec.purchase_quantity < 0:
                raise ValidationError(_('Số lượng đặt mua lớn hơn số lượng đã đặt'))

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        self.ensure_one()
        self._check_orderpoint_picking_type()
        product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
        date_planned = self.date_planned or self.order_id.date_planned
        location_dest_id = self.location_id.id if self.location_id else (
            self.order_id.location_id.id if self.order_id.location_id else False)
        if not location_dest_id:
            location_dest_id = (self.orderpoint_id and not (
                self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location()
        picking_line = picking.filtered(lambda p: p.location_dest_id and p.location_dest_id.id == location_dest_id)
        return {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.product_id.display_name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': location_dest_id,
            'picking_id': picking_line.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'description_picking': product.description_pickingin or self.name,
            'propagate_cancel': self.propagate_cancel,
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'product_packaging_id': self.product_packaging_id.id,
            'sequence': self.sequence,
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_ncc = fields.Boolean('From Ncc')
    reference = fields.Char(string='Tài liệu')

    def action_post(self):
        for rec in self:
            if rec.purchase_order_product_id:
                for item in rec.purchase_order_product_id:
                    item.write({
                        'invoice_status_fake': 'invoiced',
                    })
        res = super(AccountMove, self).action_post()
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        if self._context.get('endloop'):
            return True
        for record in self:
            po = self.env['purchase.order'].search([('name', '=', record.origin), ('is_inter_company', '=', False)],
                                                   limit=1)
            if po:
                po.write({
                    'inventory_status': 'done',
                    'invoice_status_fake': 'to invoice',
                })
                _context = {
                    'pk_no_input_warehouse': False,
                }
                if po.type_po_cost == 'tax':
                    if po.exchange_rate_line:
                       vat = self.create_invoice_po_tax(po, record)
                    if po.cost_line:
                        cp = self.create_invoice_po_cost(po, record)
                elif po.type_po_cost == 'cost':
                    cp = self.create_invoice_po_cost(po, record)
                # Tạo nhập khác xuất khác khi nhập kho
                if po.order_line_production_order and not po.is_inter_company:
                    npl = self.create_invoice_npl(po, record)
        return res

    # Xử lý nhập kho sinh bút toán ở tab chi phí po theo số lượng nhập kho
    def create_invoice_po_cost(self, po, record):
        data_in_line = po.order_line
        data_ex_line = po.exchange_rate_line
        data_co_line = po.cost_line
        list_cp_after_tax = []
        list_money = []
        before_tax = []
        if record.state == 'done':
            for po_l, pk_l in zip(po.order_line, record.move_ids_without_package):
                if pk_l.picking_id.state == 'done':
                    if pk_l.quantity_done * po_l.price_unit != 0:
                        list_money.append((pk_l.quantity_done * po_l.price_unit - po_l.discount) * po_l.order_id.exchange_rate)
            total_money = sum(list_money)
            for total in list_money:
                for co in data_co_line:
                    before_tax.append(total / total_money * co.vnd_amount)
            sum_before_tax = sum(before_tax)
            for item, exchange, total, pk_l in zip(data_in_line, data_ex_line, list_money, record.move_ids_without_package):
                if item.product_id.categ_id and item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(('Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm %s!') % item.product_id.name)
                for rec in data_co_line:
                    if rec.product_id.categ_id and rec.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                        account_acc = rec.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id
                    else:
                        raise ValidationError(('Bạn chưa cấu hình nhập kho trong danh mục sản phẩm của %s!') % rec.product_id.name)
                    if not rec.is_check_pre_tax_costs and item.order_id.type_po_cost == 'tax':
                        values = ((total + (total / total_money * rec.vnd_amount) + ((exchange.tax_amount + exchange.special_consumption_tax_amount) * pk_l.quantity_done/item.product_qty)) / (total_money + sum_before_tax)) * (rec.vnd_amount * pk_l.quantity_done/item.product_qty)
                        debit_cp = (0, 0, {
                            'sequence': 1,
                            'account_id': account_1561,
                            'product_id': item.product_id.id,
                            'name': item.name,
                            'text_check_cp_normal': rec.product_id.name,
                            'debit': values,
                            'credit': 0,
                        })
                        credit_cp = (0, 0, {
                            'sequence': 99991,
                            'account_id': account_acc,
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'text_check_cp_normal': rec.product_id.name,
                            'debit': 0,
                            'credit': values,
                        })
                        lines_cp_after_tax = [credit_cp, debit_cp]
                        list_cp_after_tax.extend(lines_cp_after_tax)
                    else:
                        debit_cp = (0, 0, {
                            'sequence': 1,
                            'account_id': account_1561,
                            'product_id': item.product_id.id,
                            'name': item.name,
                            'text_check_cp_normal': rec.product_id.name,
                            'debit': total / total_money * (rec.vnd_amount * pk_l.quantity_done/item.product_qty),
                            'credit': 0,
                        })
                        credit_cp = (0, 0, {
                            'sequence': 99991,
                            'account_id': account_acc,
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'text_check_cp_normal': rec.product_id.name,
                            'debit': 0,
                            'credit': total / total_money * (rec.vnd_amount * pk_l.quantity_done/item.product_qty),
                        })
                        lines_cp_before_tax = [credit_cp, debit_cp]
                        list_cp_after_tax.extend(lines_cp_before_tax)
            for rec in po.cost_line:
                separated_lists = {}
                invoice_line_ids = []
                target_items = rec.product_id.name
                for lines_cp_after_tax in list_cp_after_tax:
                    text_check_cp_normal = lines_cp_after_tax[2]['text_check_cp_normal']
                    if text_check_cp_normal in target_items:
                        if text_check_cp_normal in separated_lists:
                            separated_lists[text_check_cp_normal].append(lines_cp_after_tax)
                        else:
                            separated_lists[text_check_cp_normal] = [lines_cp_after_tax]
                new_lines_cp_after_tax = [lines for text_check, lines in separated_lists.items()]
                for sublist_lines_cp_after_tax in new_lines_cp_after_tax:
                    invoice_line_ids.extend(sublist_lines_cp_after_tax)
                merged_records_cp = {}
                for cp in invoice_line_ids:
                    key = (cp[2]['account_id'], cp[2]['name'], cp[2]['sequence'], cp[2]['product_id'], cp[2]['text_check_cp_normal'])
                    if key in merged_records_cp:
                        merged_records_cp[key]['debit'] += cp[2]['debit']
                        merged_records_cp[key]['credit'] += cp[2]['credit']
                    else:
                        merged_records_cp[key] = {
                            'sequence': cp[2]['sequence'],
                            'text_check_cp_normal': cp[2]['text_check_cp_normal'],
                            'account_id': cp[2]['account_id'],
                            'product_id': cp[2]['product_id'],
                            'name': cp[2]['name'],
                            'debit': cp[2]['debit'],
                            'credit': cp[2]['credit'],
                        }
                merged_records_list_cp = [(0, 0, record) for record in merged_records_cp.values()]
                entry_cp = self.env['account.move'].create({
                    'ref': f"{record.name} - {rec.product_id.name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': merged_records_list_cp,
                    'restrict_mode_hash_table': False
                })
                entry_cp.action_post()

    # Xử lý nhập kho sinh bút toán ở tab thuế nhập khẩu po theo số lượng nhập kho
    def create_invoice_po_tax(self, po, record):
        list_nk = []
        list_db = []
        invoice_line_npls = []
        cost_labor_internal_costs = []
        if record.state == 'done':
            for ex_l, pk_l in zip(po.exchange_rate_line, record.move_ids_without_package):
                if ex_l.product_id.categ_id and ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(_('Bạn chưa cấu hình tài khoản định giá tồn kho của sản phẩm %s trong danh mục của sản phẩm đó!') % ex_l.product_id.name)
                if ex_l.qty_product <= 0 and pk_l.quantity_done <= 0:
                    raise ValidationError('Số lượng của sản phẩm hay số lương hoàn thành khi nhập kho phải lớn hơn 0')
                if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế nhập khẩu'")
                if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế tiêu thụ đặc biệt'")
                debit_nk = (0, 0, {
                    'sequence': 9,
                    'account_id': account_1561,
                    'name': ex_l.name,
                    'debit': (pk_l.quantity_done / ex_l.qty_product * ex_l.tax_amount),
                    'credit': 0,
                })
                credit_nk = (0, 0, {
                    'sequence': 99991,
                    'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id.id,
                    'name': self.env.ref('forlife_purchase.product_import_tax_default').name,
                    'debit': 0,
                    'credit': (pk_l.quantity_done / ex_l.qty_product * ex_l.tax_amount),
                })
                lines_nk = [debit_nk, credit_nk]
                list_nk.extend(lines_nk)
                debit_db = (0, 0, {
                    'sequence': 9,
                    'account_id': account_1561,
                    'name': ex_l.name,
                    'debit': (pk_l.quantity_done / ex_l.qty_product * ex_l.special_consumption_tax_amount),
                    'credit': 0,
                })
                credit_db = (0, 0, {
                    'sequence': 99991,
                    'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id.id,
                    'name': self.env.ref('forlife_purchase.product_excise_tax_default').name,
                    'debit': 0,
                    'credit': (pk_l.quantity_done / ex_l.qty_product * ex_l.special_consumption_tax_amount),
                })
                lines_db = [debit_db, credit_db]
                list_db.extend(lines_db)
            merged_records_tnk = {}
            merged_records_db= {}
            for tnk in list_nk:
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
            merged_records_list_tnk = [(0, 0, record) for record in merged_records_tnk.values()]
            for db in list_db:
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
            merged_records_list_db = [(0, 0, record) for record in merged_records_db.values()]
            entry_nk = self.env['account.move'].create({
                'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_import_tax_default').name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'exchange_rate': po.exchange_rate,
                'date': datetime.now(),
                'invoice_payment_term_id': po.payment_term_id.id,
                'invoice_date_due': po.date_planned,
                'invoice_line_ids': merged_records_list_tnk,
                'restrict_mode_hash_table': False
            })
            entry_nk.action_post()
            entry_db = self.env['account.move'].create({
                'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_excise_tax_default').name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'exchange_rate': po.exchange_rate,
                'date': datetime.now(),
                'invoice_payment_term_id': po.payment_term_id.id,
                'invoice_date_due': po.date_planned,
                'invoice_line_ids': merged_records_list_db,
                'restrict_mode_hash_table': False
            })
            entry_db.action_post()

    # Xử lý nhập kho sinh bút toán ở tab npl po theo số lượng nhập kho + sinh bút toán cho chi phí nhân công nội địa
    def create_invoice_npl(self, po, record):
        list_money = []
        list_cp = []
        list_npls = []
        list_line_xk = []
        cost_labor_internal_costs = []
        if record.state == 'done':
            for po_l, pk_l in zip(po.order_line, record.move_ids_without_package):
                if pk_l.picking_id.state == 'done':
                    if pk_l.quantity_done * po_l.price_unit != 0:
                        list_money.append(pk_l.quantity_done * po_l.price_unit - po_l.discount)
            total_money = sum(list_money)
            for item, r, total in zip(po.order_line_production_order, record.move_ids_without_package, list_money):
                material = self.env['purchase.order.line.material.line'].search([('purchase_order_line_id', '=', item.id)])
                if item.product_id.categ_id and item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(_("Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm có tên %s") % item.product_id.name)
                debit_cost = 0
                for material_line in material:
                    if material_line.product_id.product_tmpl_id.x_type_cost_product in ('labor_costs', 'internal_costs'):
                        if not material_line.product_id.categ_id or not material_line.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id:
                            raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho trong danh mực sản phẩm của %s") % material_line.product_id.name)
                        pbo = material_line.price_unit * r.quantity_done/item.product_qty * item.order_id.exchange_rate
                        credit_cp = (0, 0, {
                            'sequence': 99991,
                            'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id,
                            'product_id': material_line.product_id.id,
                            'name': material_line.product_id.name,
                            'text_check_cp_normal': item.product_id.name,
                            'debit': 0,
                            'credit': pbo,
                        })
                        cost_labor_internal_costs.append(credit_cp)
                        debit_cost += pbo
                    else:
                        if not self.env.ref('forlife_stock.export_production_order').with_company(record.company_id).x_property_valuation_in_account_id:
                            raise ValidationError('Bạn chưa cấu hình tài khoản trong lý do xuất nguyên phụ liệu')
                        list_line_xk.append((0, 0, {
                            'product_id': material_line.product_id.id,
                            'product_uom': material_line.uom.id,
                            'price_unit': material_line.price_unit,
                            'location_id': record.location_dest_id.id,
                            'location_dest_id': self.env.ref('forlife_stock.export_production_order').id,
                            'product_uom_qty': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'quantity_done': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'amount_total': material_line.price_unit * material_line.product_qty,
                            'reason_type_id': self.env.ref('forlife_stock.reason_type_6').id,
                            'reason_id': self.env.ref('forlife_stock.export_production_order').id,
                        }))
                        ### tạo bút toán npl
                        if item.product_id.id == material_line.purchase_order_line_id.product_id.id:
                            debit_npl = (0, 0, {
                                'sequence': 9,
                                'account_id': self.env.ref('forlife_stock.export_production_order').with_company(record.company_id).x_property_valuation_in_account_id.id,
                                'name': self.env.ref('forlife_stock.export_production_order').with_company(record.company_id).x_property_valuation_in_account_id.name,
                                'debit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price) * item.order_id.exchange_rate,
                                'credit': 0,
                            })
                            credit_npl = (0, 0, {
                                'sequence': 99991,
                                'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id,
                                'name': material_line.product_id.name,
                                'debit': 0,
                                'credit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price) * item.order_id.exchange_rate,
                            })
                            lines_npl = [debit_npl, credit_npl]
                            list_npls.extend(lines_npl)
                debit_cp = (0, 0, {
                    'sequence': 9,
                    'account_id': account_1561,
                    'product_id': item.product_id.id,
                    'name': item.product_id.name,
                    'text_check_cp_normal': item.product_id.name,
                    'debit': debit_cost,
                    'credit': 0,
                })
                cost_labor_internal_costs.append(debit_cp)
                separated_lists = {}
                invoice_line_ids = []
                target_items = item.product_id.name
                for lines_new in cost_labor_internal_costs:
                    text_check_cp_normal = lines_new[2]['text_check_cp_normal']
                    if text_check_cp_normal in target_items:
                        if text_check_cp_normal in separated_lists:
                            separated_lists[text_check_cp_normal].append(lines_new)
                        else:
                            separated_lists[text_check_cp_normal] = [lines_new]
                new_lines_cp_after_tax = [lines for text_check, lines in separated_lists.items()]
                for sublist_lines_cp_after_tax in new_lines_cp_after_tax:
                    invoice_line_ids.extend(sublist_lines_cp_after_tax)
                entry_cp = self.env['account.move'].create({
                    'ref': f"{record.name} - Chi phí nhân công thuê ngoài/nội bộ - {target_items}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': invoice_line_ids,
                    'restrict_mode_hash_table': False
                })
                entry_cp.action_post()

            if list_npls and list_line_xk:
                merged_records_npl = {}
                for npl in list_npls:
                    key = (npl[2]['account_id'], npl[2]['name'], npl[2]['sequence'])
                    if key in merged_records_npl:
                        merged_records_npl[key]['debit'] += npl[2]['debit']
                        merged_records_npl[key]['credit'] += npl[2]['credit']
                    else:
                        merged_records_npl[key] = {
                            'sequence': npl[2]['sequence'],
                            'account_id': npl[2]['account_id'],
                            'name': npl[2]['name'],
                            'debit': npl[2]['debit'],
                            'credit': npl[2]['credit'],
                        }
                merged_records_list_npl = [(0, 0, record) for record in merged_records_npl.values()]
                if merged_records_list_npl:
                    entry_npls = self.env['account.move'].create({
                        'ref': f"{record.name} - Nguyên phụ liệu",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_npl,
                        'restrict_mode_hash_table': False
                    })
                    entry_npls.action_post()
                    if record.state == 'done':
                        master_xk = self.create_xk_picking(po, record, list_line_xk, entry_npls)

    ###tự động tạo phiếu xuất khác và hoàn thành khi nhập kho hoàn thành
    def create_xk_picking(self, po, record, list_line_xk, account_move=None):
        company_id = self.env.company.id
        picking_type_out = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', company_id)], limit=1)
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'location_id': record.location_dest_id.id,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_6').id,
            'location_dest_id': self.env.ref('forlife_stock.export_production_order').id,
            'scheduled_date': datetime.now(),
            'origin': po.name,
            'other_export': True,
            'state': 'assigned',
            'picking_type_id': picking_type_out.id,
            'move_ids_without_package': list_line_xk
        }
        xk_picking = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(master_xk)
        xk_picking.button_validate()
        if account_move:
            xk_picking.write({'account_xk_id': account_move.id})
        record.write({'picking_xk_id': xk_picking.id})
        return xk_picking


class Synthetic(models.Model):
    _name = 'forlife.synthetic'

    synthetic_id = fields.Many2one('purchase.order')

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
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)', compute='_compute_after_tax', store=1)
    total_product = fields.Float(string='Tổng giá trị tiền hàng', compute='_compute_total_product', store=1)

    @api.depends('synthetic_id.cost_line.is_check_pre_tax_costs')
    def _compute_is_check_pre_tax_costs(self):
        for rec in self:
            cost_line = rec.synthetic_id.cost_line
            for line in rec.synthetic_id.exchange_rate_line:
                total_cost_true = 0
                if cost_line:
                    for item in cost_line:
                        if item.is_check_pre_tax_costs or not item.is_check_pre_tax_costs:
                            if item.vnd_amount and rec.price_subtotal > 0:
                                before_tax = (rec.price_subtotal / sum(self.mapped('price_subtotal'))) * item.vnd_amount
                                total_cost_true += before_tax
                            rec.before_tax = total_cost_true
                if rec.product_id.id == line.product_id.id:
                    line.vnd_amount = rec.price_subtotal + rec.before_tax

    @api.depends('before_tax', 'tnk_tax', 'db_tax', 'price_subtotal')
    def _compute_after_tax(self):
        for rec in self:
            for line in rec.synthetic_id.exchange_rate_line:
                total_cost = 0
                for item in rec.synthetic_id.cost_line:
                    if rec.synthetic_id.type_po_cost == 'tax':
                        if rec.price_subtotal > 0:
                            total_cost += ((rec.price_subtotal + rec.before_tax + line.tax_amount + line.special_consumption_tax_amount) / (sum(self.mapped('price_subtotal')) + sum(self.mapped('before_tax')))) * item.vnd_amount
                            rec.after_tax = total_cost
                    else:
                        rec.after_tax = 0

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
