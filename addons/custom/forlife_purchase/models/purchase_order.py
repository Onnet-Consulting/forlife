from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby, float_round
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
        ('product', 'Hàng hóa'),
        ('service', 'Dịch vụ'),
        ('asset', 'Tài sản'),
    ], string='Purchase Type', default='product', copy=False)

    inventory_status = fields.Selection([
        ('not_received', 'Not Received'),
        ('incomplete', 'Incomplete'),
        ('done', 'Done'),
    ], string='Inventory Status', default='not_received', compute='compute_inventory_status', store=1)

    purchase_code = fields.Char(string='Internal order number')
    has_contract = fields.Boolean(string='Hợp đồng khung?')
    has_invoice = fields.Boolean(string='Finance Bill?')
    exchange_rate = fields.Float(string='Tỷ giá ', default=1)
    partner_id = fields.Many2one('res.partner', string='Nhà cung cấp', required=True, states=READONLY_STATES, change_default=True, tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="You can find a vendor by its Name, TIN, Email or Internal Reference.")

    # apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange', compute='_compute_active_manual_currency_rate')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency',
                                                 compute='_compute_active_manual_currency_rate', store=1)
    production_id = fields.Many2one('forlife.production', string='Production Order', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], copy=False)
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
    select_type_inv = fields.Selection(
        copy=False,
        # default='normal',
        string="Loại hóa đơn",
        required=True,
        selection=[('expense', 'Hóa đơn chi phí mua hàng'),
                   ('labor', 'Hóa đơn chi phí nhân công'),
                   ('normal', 'Hóa đơn chi tiết hàng hóa'),
                   ])
    cost_line = fields.One2many('purchase.order.cost.line', 'purchase_order_id', copy=True, string="Chi phí ước tính")
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    location_id = fields.Many2one('stock.location', string="Kho nhận", check_company=True)
    is_inter_company = fields.Boolean(default=False)
    partner_domain = fields.Char()
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True, domain=False,
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    occasion_code_id = fields.Many2one('occasion.code', string="Case Code", copy=False)
    account_analytic_id = fields.Many2one('account.analytic.account', copy=False,
                                            string="Cost Center")
    is_purchase_request = fields.Boolean(default=False, copy=False)
    is_check_readonly_partner_id = fields.Boolean(copy=False)
    is_check_readonly_purchase_type = fields.Boolean(copy=False)
    source_document = fields.Char(string="Source Document")
    receive_date = fields.Datetime(string='Receive Date')
    note = fields.Char('Note')
    source_location_id = fields.Many2one('stock.location', string="Địa điểm nguồn")
    trade_discount = fields.Float(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Float(string='Tổng chiết khấu thương mại')
    x_tax = fields.Float(string='Thuế VAT cùa chiết khấu(%)')
    x_amount_tax = fields.Float(string='Tiền VAT của chiết khấu', compute='compute_x_amount_tax', store=1, readonly=False)
    location_export_material_id = fields.Many2one('stock.location', string='Địa điểm xuất NPL')

    @api.depends('total_trade_discount', 'x_tax')
    def compute_x_amount_tax(self):
        for rec in self:
            if rec.total_trade_discount > 0 and rec.x_tax > 0:
                rec.x_amount_tax = rec.x_tax / 100 * rec.total_trade_discount

    @api.constrains('x_tax')
    def constrains_x_tax(self):
        for rec in self:
            if rec.x_tax > 100 or rec.x_tax < 0:
                raise UserError(_('Bạn khổng thể nhập % thuế VAT của chiết khấu nhỏ hơn 0 hoặc lớn hơn 100!'))


    count_invoice_inter_company_ncc = fields.Integer(compute='compute_count_invoice_inter_company_ncc')
    count_invoice_inter_normal_fix = fields.Integer(compute='compute_count_invoice_inter_normal_fix')
    count_invoice_inter_expense_fix = fields.Integer(compute='compute_count_invoice_inter_expense_fix')
    count_invoice_inter_labor_fix = fields.Integer(compute='compute_count_invoice_inter_labor_fix')
    # count_invoice_inter_service_fix = fields.Integer(compute='compute_count_invoice_inter_service_fix')
    count_invoice_inter_company_customer = fields.Integer(compute='compute_count_invoice_inter_company_customer')
    count_delivery_inter_company = fields.Integer(compute='compute_count_delivery_inter_company')
    count_delivery_import_inter_company = fields.Integer(compute='compute_count_delivery_import_inter_company')
    cost_total = fields.Float(string='Tổng chi phí', compute='compute_cost_total', store=1)
    is_done_picking = fields.Boolean(default=False, compute='compute_is_done_picking')

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
    date_order = fields.Datetime('Order Deadline', states=READONLY_STATES, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")
    currency_id = fields.Many2one('res.currency', 'Currency', states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    rejection_reason = fields.Char(string="Lý do từ chối")
    cancel_reason = fields.Char(string="Lý do huỷ")
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)", compute='compute_origin', store=1)
    type_po_cost = fields.Selection([('tax', 'Tax'), ('cost', 'Cost')])
    purchase_synthetic_ids = fields.One2many(related='order_line')
    exchange_rate_line_ids = fields.One2many(related='order_line', string='Thuế nhập khẩu')
    show_check_availability = fields.Boolean(
        compute='_compute_show_check_availability', invisible=True,
        help='Technical field used to compute whether the button "Check Availability" should be displayed.')

    # Lấy của base về phục vụ import
    payment_term_id = fields.Many2one('account.payment.term', 'Chính sách thanh toán',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    partner_company_id = fields.Many2one(comodel_name='res.company', compute='_compute_partner_company_id', index=True, store=True)

    @api.depends('partner_id')
    def _compute_partner_company_id(self):
        partner_company = {
            company.partner_id.id: company
            for company in self.env['res.company'].sudo().search([('partner_id', 'in', self.mapped('partner_id.id'))])
        }
        for rec in self:
            rec.partner_company_id = partner_company.get(rec.partner_id.id)

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

    date_planned = fields.Datetime(
        string='Expected Arrival', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")

    date_planned_import = fields.Datetime('Hạn xử lý')
    count_stock = fields.Integer(compute="compute_count_stock", copy=False)

    @api.depends('order_line.date_planned', 'date_planned_import')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped(
                'date_planned')
            if not order.date_planned_import:
                if dates_list:
                    order.date_planned = min(dates_list)
                else:
                    order.date_planned = False
            else:
                order.date_planned = order.date_planned_import

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        if self.date_planned:
            self.order_line.filtered(lambda line: not line.display_type).date_planned = self.date_planned

    @api.onchange('partner_id')
    def onchange_vendor_code(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id

    def compute_count_stock(self):
        for item in self:
            item.count_stock = self.env['stock.picking'].search_count([('origin', '=', item.name), ('other_export', '=', True)])

    @api.onchange('location_id')
    def _onchange_line_location_id(self):
        for rec in self.order_line:
            rec.location_id = self.location_id

    @api.onchange('account_analytic_id')
    def _onchange_line_account_analytic_id(self):
        for rec in self.order_line:
            rec.account_analytic_id = self.account_analytic_id._origin if self.account_analytic_id else None

    @api.onchange('occasion_code_id')
    def _onchange_line_occasion_code_id(self):
        for rec in self.order_line:
            rec.occasion_code_id = self.occasion_code_id._origin if self.occasion_code_id else None

    @api.onchange('production_id')
    def _onchange_line_production_id(self):
        for rec in self.order_line:
            rec.production_id = self.production_id._origin if self.production_id else None

    @api.onchange('receive_date')
    def _onchange_line_receive_date(self):
        for rec in self.order_line:
            rec.receive_date = self.receive_date

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        res = super().onchange_partner_id_warning()
        if self.purchase_type == 'product':
            if self.partner_id and self.order_line and self.currency_id:
                for item in self.order_line:
                    if item.product_id:
                        item.product_uom = item.product_id.uom_id.id
                        date_item = datetime.now().date()
                        supplier_info = self.env['product.supplierinfo'].search(
                            [('product_id', '=', item.product_id.id),
                             ('partner_id', '=', self.partner_id.id),
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
        else:
            pass

        if self.partner_id and self.sudo().source_location_id.company_id and self.env['res.company'].sudo().search([
            ('partner_id', '=', self.partner_id.id),
            ('id', '!=', self.sudo().source_location_id.company_id.id)
        ]):
            self.source_location_id = None

        # Do something with res
        return res

    # @api.constrains('account_analytic_ids')
    # def constrains_account_analytic_ids(self):
    #     for item in self:
    #         if not item.is_purchase_request and item.account_analytic_ids and len(item.account_analytic_ids) > 1:
    #             raise ValidationError('Bạn chỉ được chọn một 1 trung tâm chi phí')

    # @api.constrains('occasion_code_ids')
    # def constrains_occasion_code_ids(self):
    #     for item in self:
    #         if not item.is_purchase_request and item.occasion_code_ids and len(item.occasion_code_ids) > 1:
    #             raise ValidationError('Bạn chỉ được chọn một 1 mã vụ việc')

    # @api.constrains('production_id')
    # def constrains_production_id(self):
    #     for item in self:
    #         if not item.is_purchase_request and item.production_id and len(item.production_id) > 1:
    #             raise ValidationError('Bạn chỉ được chọn một 1 lệnh sản xuất')

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            if self.type_po_cost != 'cost':
                self.exchange_rate = self.currency_id.inverse_rate
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

    # def action_view_invoice_customer(self):
    #     for item in self:
    #         customer = self.data_account_move([('reference', '=', item.name), ('is_from_ncc', '=', False)])
    #         context = {'create': True, 'delete': True, 'edit': True}
    #         return {
    #             'name': _('Hóa đơn bán hàng'),
    #             'view_mode': 'tree,form',
    #             'res_model': 'account.move',
    #             'type': 'ir.actions.act_window',
    #             'target': 'current',
    #             'domain': [('id', 'in', customer.ids)],
    #             'context': context
    #         }

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

    def compute_count_invoice_inter_normal_fix(self):
        for rec in self:
            domain_moves_normal = [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'normal')]
            rec.count_invoice_inter_normal_fix = self.env['account.move'].search_count(domain_moves_normal)

    def compute_count_invoice_inter_expense_fix(self):
        for rec in self:
            rec.count_invoice_inter_expense_fix = self.env['account.move'].search_count(
                [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'expense')])

    def compute_count_invoice_inter_labor_fix(self):
        for rec in self:
            rec.count_invoice_inter_labor_fix = self.env['account.move'].search_count(
                [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'labor')])

    # def compute_count_invoice_inter_service_fix(self):
    #     for rec in self:
    #         rec.count_invoice_inter_service_fix = self.env['account.move'].search_count(
    #             [('purchase_order_product_id', 'in', rec.id), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'service')])

    @api.onchange('trade_discount')
    def onchange_total_trade_discount(self):
        if self.trade_discount:
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_total') * (self.trade_discount / 100)

    @api.onchange('total_trade_discount')
    def onchange_trade_discount(self):
        if self.total_trade_discount:
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.trade_discount = self.total_trade_discount / self.tax_totals.get('amount_total') * 100

    def action_confirm(self):
        for record in self:
            if record.purchase_type == 'asset':
                for item in record.order_line:
                    if item.asset_code.asset_account.code != item.product_id.categ_id.with_company(
                            item.company_id).property_account_expense_categ_id.code:
                        raise ValidationError(
                            'Tài khoản trong Mã tài sản của bạn khác với tài khoản chi phí trong nhóm sản phẩm')

            if not record.partner_id:
                raise UserError("Bạn chưa chọn nhà cung cấp!!")
            list_line_invalid = []
            for r in record.order_line:
                if not record.partner_id.is_passersby:
                    supplier = self.env['product.supplierinfo'].search([('partner_id', '=', record.partner_id.id),('product_id','=',r.product_id.id)],limit=1)
                    if not supplier:
                        pass
                    else:
                        #validate
                        supplier_exits = self.env['product.supplierinfo'].search([('amount_conversion','=',r.exchange_quantity),('partner_id', '=', record.partner_id.id),('product_id','=',r.product_id.id)],limit=1)
                        if not supplier_exits:
                            list_line_invalid.append(r.product_id.name_get()[0][1])
            if list_line_invalid:
                mgs = f"Sản phẩm {',  '.join(list_line_invalid)} có số lượng quy đổi không khớp với nhà cung cấp {record.partner_id.name_get()[0][1]} \n"
                raise UserError(_(mgs))
            product_discount_tax = self.env.ref('forlife_purchase.product_discount_tax', raise_if_not_found=False)
            if product_discount_tax and any(line.product_id.id == product_discount_tax.id and line.price_unit > 0 for line in record.order_line):
                raise UserError("Giá CTKM phải = 0. Người dùng vui lòng nhập đơn giá ở phần thông tin tổng chiết khấu thương mại.")
            for orl in record.order_line:
                if orl.product_id.id == self.env.ref('forlife_purchase.product_discount_tax').id or orl.free_good:
                    continue
                if orl.price_subtotal <= 0:
                    raise UserError(_('Đơn hàng chứa sản phẩm %s có tổng tiền bằng 0!') % orl.product_id.name)
            record.write({'custom_state': 'confirm'})

    def action_approved_vendor(self, data, order_line, invoice_line_ids):
        so = self.env['sale.order'].sudo().create({
            'company_id': self.source_location_id.company_id.id,
            'origin': data.get('name'),
            'partner_id': self.env.user.partner_id.id,
            'payment_term_id': data.get('payment_term_id'),
            'state': 'sent',
            'date_order': data.get('date_order'),
            'warehouse_id': self.source_location_id.warehouse_id.id,
            'order_line': [(0, 0, {
                'product_id': item.get('product_id'),
                'name': item.get('name'),
                'product_uom_qty': item.get('product_quantity'), 'price_unit': item.get('price_unit'),
                'product_uom': item.get('product_uom'),
                'customer_lead': 0, 'sequence': 10, 'is_downpayment': False, 'is_expense': True,
                'qty_delivered_method': 'analytic',
                'discount': item.get('discount_percent')
            }) for item in order_line]
        })
        so.with_context(from_inter_company=True, company_po=self.source_location_id.company_id.id).action_confirm()
        return so

    def approve_company_picking(self, sale):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('exchange_code', '=', False), ('company_id', '=', sale.company_id.id)], limit=1)
        picking = self.env['stock.picking'].with_context(auto_done=True).create({
            'origin': sale.name,
            'company_id': sale.company_id.id,
            'move_type': sale.picking_policy,
            'partner_id': sale.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'sale_id': sale.id,
            'move_ids_without_package': [(0, 0, {
                'name': sol.name,
                'product_id': sol.product_id.id,
                'product_uom': sol.product_uom.id,
                'product_uom_qty': sol.product_uom_qty,
                'procure_method': 'make_to_stock',
                'origin': sol.order_id.name,
                'date_deadline': datetime.utcnow(),
                'description_picking': sol.name,
                'sale_line_id': sol.id,
                'occasion_code_id': sol.x_occasion_code_id,
                'work_production': sol.x_manufacture_order_code_id,
                'account_analytic_id': sol.x_account_analytic_id,
                'company_id': sale.company_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id
            }) for sol in sale.order_line if sol.product_id.detailed_type == 'product']
        })

        picking.action_confirm()
        picking.action_assign()
        materials_not_enough = '\n\t- '.join([
            sm.product_id.name if not sm.product_id.barcode else f'[{sm.product_id.barcode}] {sm.product_id.name}'
            for sm in picking.move_ids_without_package if sm.state != 'assigned'
        ])
        if materials_not_enough:
            raise ValidationError(_('Kho "%s" không đủ tồn kho:\n\t- %s', picking.location_id.complete_name, materials_not_enough))
        picking.button_validate()
        return picking

    def approve_company_sale(self, company_sale):
        sale = self.env['sale.order'].create({
            'company_id': company_sale.id,
            'origin': self.name,
            'partner_id': self.env.company.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'state': 'sent',
            'date_order': self.date_order,
            'order_line': [(0, 0, {
                'product_id': pol.product_id.id,
                'name': pol.name,
                'product_uom_qty': pol.product_uom_qty,
                'price_unit': pol.price_unit or float_round(pol.price_subtotal / pol.product_uom_qty, 0),
                'product_uom': pol.product_uom.id,
                'customer_lead': 0,
                'sequence': 10,
                'is_downpayment': False,
                'is_expense': True,
                'discount': pol.discount_percent,
                'company_id': company_sale.id
            }) for pol in self.order_line]
        })
        picking = self.approve_company_picking(sale)
        sale.state = 'sale'

        invoice_values = sale._prepare_invoice()
        invoice_values['invoice_line_ids'] = [(0, 0, sol._prepare_invoice_line(quantity=sol.product_uom_qty)) for sol in sale.order_line]
        invoice = self.env['account.move'].create(invoice_values)
        invoice._post()
        return sale, invoice, picking

    def action_approved_inter_company(self):
        company_sale = self.env['res.company'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)
        sale, invoice, picking = self.with_company(company_sale).approve_company_sale(company_sale)
        picking_type_in = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('exchange_code', '=', False)], limit=1)
        vendor_picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'partner_id': company_sale.partner_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.location_id.id,
            'scheduled_date': datetime.utcnow(),
            'date_done': self.receive_date,
            'origin': self.name,
            'move_ids_without_package': [(0, 0, {
                'name': pol.name,
                'product_id': pol.product_id.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': self.location_id.id,
                'product_uom_qty': pol.product_uom_qty,
                'price_unit': float_round(pol.price_subtotal / pol.product_uom_qty, 0),
                'product_uom': pol.product_uom.id,
                'quantity_done': pol.product_uom_qty,
                'purchase_line_id': pol.id
            }) for pol in self.order_line if pol.product_id.detailed_type == 'product'],
        })
        vendor_picking.action_confirm()
        vendor_picking.action_assign()
        vendor_picking.button_validate()

        invoice_vals = self._prepare_invoice()
        invoice_vals.update({
            'purchase_type': self.purchase_type,
            'invoice_date': datetime.utcnow(),
            'exchange_rate': self.exchange_rate,
            'currency_id': self.currency_id.id,
            'move_type': 'in_invoice',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, pol._prepare_account_move_line()) for pol in self.order_line]
        })
        vendor_bill = self.env['account.move'].create(invoice_vals)
        vendor_bill._post()

        self.write({
            'custom_state': 'approved',
            'inventory_status': 'incomplete',
            'invoice_status_fake': 'no',
            'picking_ids': [(6, 0, vendor_picking.ids)],
            'invoice_ids': [(6, 0, vendor_bill.ids)]
        })

    def validate_inter_purchase_order(self):
        domain_location = ('location_id', '=', self.source_location_id.id) if not self.is_return else ('location_id', '=', self.location_id.id)
        for line in self.order_line:
            if line.price_subtotal <= 0 and not line.free_good:
                raise UserError('Bạn không thể phê duyệt với đơn mua hàng có thành tiền bằng 0!')
            product_ncc = self.env['stock.quant'].sudo().search([domain_location, ('product_id', '=', line.product_id.id)]).mapped('quantity')
            if sum(product_ncc) < line.product_qty:
                raise ValidationError('Số lượng sản phẩm (%s) trong kho không đủ.' % (line.product_id.name))

    def _create_sale_order_another_company(self):
        sale_order_lines = []
        all_tax_ids = self.env['account.tax'].sudo().search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.source_location_id[0].company_id.id)
        ])
        for item in self.order_line:
            tax_ids = []
            if item.taxes_id:
                tax_ids = all_tax_ids.filtered(lambda x: x.amount in item.taxes_id.mapped('amount')).ids

            sale_order_lines.append((0, 0, {
                'product_id': item.product_id.id,
                'name': item.product_id.name,
                'product_uom_qty': item.product_qty,
                'price_unit': item.price_unit,
                'product_uom': item.product_id.uom_id.id,
                'customer_lead': 0,
                'sequence': 10,
                'is_downpayment': False,
                'is_expense': True,
                'qty_delivered_method': 'analytic',
                'discount': item.discount_percent,
                'x_location_id': self.source_location_id.id,
                'tax_id': [(6, 0, tax_ids)],
            }))

        sale_order_vals = {
            'company_id': self.source_location_id[0].company_id.id,
            'origin': self.name,
            'partner_id': self.company_id.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'date_order': self.date_order,
            'warehouse_id': self.source_location_id[0].warehouse_id.id,
            'x_location_id': self.source_location_id.id,
            'order_line': sale_order_lines
        }
        sale_id = self.env['sale.order'].sudo().create(sale_order_vals)
        return sale_id

    def action_approved(self):
        # self.check_purchase_tool_and_equipment()
        for record in self:
            if not record.is_inter_company:
                super(PurchaseOrder, self).button_confirm()
                picking_in = self.env['stock.picking'].search([('origin', '=', record.name)])
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
                                'account_analytic_id': orl.account_analytic_id.id,
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
                                'free_good': orl.free_good,
                                'purchase_uom': orl.purchase_uom.id,
                                'quantity_change': orl.exchange_quantity,
                                'quantity_purchase_done': orl.product_qty / orl.exchange_quantity if orl.exchange_quantity else False,
                                'occasion_code_id': orl.occasion_code_id.id,
                                'work_production': orl.production_id.id,
                                'account_analytic_id': orl.account_analytic_id.id,
                            })
                record.write({'custom_state': 'approved'})
            else:
                if not record.is_return:
                    self.action_approve_inter_company()
                else:
                    self.action_approve_inter_company_return()

                return True

    def action_approve_inter_company(self):
        self.sudo().with_context(inter_company=True)
        self.validate_inter_purchase_order()
        self.button_confirm()
        picking_in = self.picking_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
        if picking_in:
            picking_in.move_line_ids_without_package.write({
                'location_dest_id': self.location_id.id
            })
            picking_in.action_set_quantities_to_reservation()
            picking_in.button_validate()
            if picking_in.state == 'done':
                self.write({
                    'select_type_inv': 'normal',
                    'custom_state': 'approved',
                    'inventory_status': 'done',
                })
                invoice = self.action_create_invoice()
                invoice.action_post()
        else:
            raise UserError('Phiếu nhập kho chưa được hoàn thành, vui lòng kiểm tra lại!')

        sale_id = self.sudo()._create_sale_order_another_company()
        sale_id.action_create_picking()
        picking_out = sale_id.picking_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
        if picking_out:
            picking_out.action_set_quantities_to_reservation()
            picking_out.button_validate()
            if picking_out.state == 'done':
                for move_id in picking_out.move_ids:
                    move_id.sale_line_id.qty_delivered = move_id.quantity_done
                invoice_customer = self.env['sale.advance.payment.inv'].sudo().create({
                    'sale_order_ids': [(6, 0, sale_id.ids)],
                    'advance_payment_method': 'delivered',
                    'deduct_down_payments': True,
                }).forlife_create_invoices()
                invoice_customer.action_post()

    def action_approve_inter_company_return(self):
        self.sudo().with_context(inter_company=True)
        self.validate_inter_purchase_order()
        self.button_confirm()
        picking_out = self.picking_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
        if picking_out:
            picking_out.move_ids_without_package.write({
                'location_id': self.location_id.id,
                'location_dest_id': self.partner_id.property_stock_supplier.id
            })
            picking_out.move_line_ids_without_package.write({
                'location_id': self.location_id.id,
                'location_dest_id': self.partner_id.property_stock_supplier.id
            })
            picking_out.action_set_quantities_to_reservation()
            picking_out.button_validate()
            if picking_out.state == 'done':
                self.write({
                    'select_type_inv': 'normal',
                    'custom_state': 'approved',
                    'inventory_status': 'done',
                })
                invoice = self.action_create_invoice()
                invoice.action_post()
        else:
            raise UserError('Phiếu nhập kho chưa được hoàn thành, vui lòng kiểm tra lại!')

    def check_purchase_tool_and_equipment(self):
        # Kiểm tra xem có phải sp CCDC không (có category đc cấu hình trường tài khoản định giá tồn kho là 153)
        # kiểm tra Đơn Giá mua trên PO + Giá trị chi phí được phân bổ  <> giá trung bình kho của sản phẩm, thì thông báo Hiển thị thông báo cho người dùng: Giá của sản phẩm CCDC này # giá nhập vào đợt trước.Yêu cầu người dùng tạo sản phẩm mới.
        # Nếu Tồn kho = 0 : cho phép nhập giá mới trên line, xác nhận PO và tiến hành nhập kho.
        for rec in self:
            if rec.order_line:
                location_id = rec.location_id
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
                            if line.location_id:
                                number_product = self.env['stock.quant'].search(
                                    [('location_id', '=', line.location_id.id), ('product_id', '=', line.product_id.id)])
                            else:
                                number_product = self.env['stock.quant'].search(
                                    [('location_id', '=', location_id.id), ('product_id', '=', line.product_id.id)])
                            if number_product and sum(number_product.mapped('quantity')) > 0:
                                if line.product_id.standard_price != line.price_unit + cost_total / count_ccdc_product:
                                    product_ccdc_diff_price.append(line.product_id.display_name)
                    if product_ccdc_diff_price:
                        raise UserError("Giá sản phẩm công cụ dụng cụ %s khác giá nhập vào đợt trước. Yêu cầu người dùng tạo sản phẩm mới." % ",".join(product_ccdc_diff_price))

    def supplier_sales_order(self, data, order_line, invoice_line_ids):
        company_partner = self.env.company.partner_id
        # fixme: Why find a random (3000) partner?
        # if not company_partner:
        #     company_partner = self.env['res.partner'].search([('group_id.code', '=', '3000')], limit=1)

        if company_partner:
            picking_type_in = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', self.env.company.id)], limit=1)
            data_all_picking = {}
            order_line_so = []
            property_stock_customer = self.company_id.partner_id.property_stock_customer.id
            for item in order_line:
                key_location = 1
                picking_line = (0, 0, {
                    'product_id': item.get('product_id'),
                    'name': item.get('name'),
                    'location_dest_id': key_location,
                    'location_id': property_stock_customer,
                    'product_uom_qty': item.get('product_quantity'),
                    'price_unit': item.get('price_unit'),
                    'product_uom': item.get('product_uom'),
                    'reason_id': data.get('location_id'),
                    'quantity_done': item.get('product_quantity')
                })
                picking_master = {
                    'picking_type_id': picking_type_in.id,
                    'partner_id': company_partner.id,
                    'location_id': property_stock_customer,
                    'location_dest_id': key_location,
                    'scheduled_date': datetime.now(),
                    'date_done': data.get('deceive_date'),
                    'move_ids_without_package': [picking_line],
                    'origin': data.get('name'),
                    'purchase_id': self.id
                }
                if data_all_picking.get(key_location):
                    data_all_picking.get(key_location).get('move_ids_without_package').append(picking_line)
                else:
                    data_all_picking.update({
                        key_location: picking_master
                    })
                order_line_so.append((0, 0, {
                    'product_id': item.get('product_id'),
                    'name': item.get('name'),
                    'product_uom_qty': item.get('product_quantity'),
                    'price_unit': item.get('price_unit'),
                    'product_uom': item.get('product_uom'),
                    'customer_lead': 0, 'sequence': 10,
                    'is_downpayment': False,
                    'is_expense': True,
                    'qty_delivered_method': 'analytic',
                    'discount': item.get('discount_percent')
                }))

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
            data_so.with_context({'from_inter_company': True, 'company_po': self.source_location_id[0].company_id.id}).action_confirm()
            data_stp_out = self.env['stock.picking'].search([('sale_id', '=', data_so.id)], limit=1)
            # data_stp_out.write({
            #     'company_id': self.source_location_id[0].company_id.id
            # })
            # for item in data_so.picking_ids:
            #     item.write({
            #         'location_id': data.get('source_location_id'),
            #         'location_dest_id': data.get('location_id')
            #     })
            data_stp_out.action_set_quantities_to_reservation()
            data_stp_out.button_validate()
            for spl, sol in zip(data_stp_out.move_ids_without_package, data_so.order_line):
                # spl.write({'quantity_done': pol.get('product_quantity'), })
                sol.write({'qty_delivered': spl.quantity_done})
            # Sử lý hóa đơn
            invoice_ncc = self.env['sale.advance.payment.inv'].sudo().create({
                'sale_order_ids': [(6, 0, data_so.ids)],
                'advance_payment_method': 'delivered',
                'deduct_down_payments': True,
            }).forlife_create_invoices()
            invoice_ncc.action_post()
            # invoice_ncc.invoice_line_ids = None
            # invoice_ncc.invoice_line_ids = invoice_line_ids
            invoice_customer = invoice_ncc.copy({
                'invoice_line_ids': []
            })
            # invoice_ncc.write({
            #     'purchase_type': data.get('purchase_type'),
            #     'move_type': 'out_invoice',
            #     'reference': data_so.name,
            #     'is_from_ncc': True
            # })
            # Vào sổ hóa đơn bán hàng
            invoice_customer.write({
                'invoice_date': datetime.now(),
                'move_type': 'in_invoice',
                'reference': data.get('name'),
                'is_from_ncc': False,
                'partner_id': data.get('partner_id'),
                'invoice_line_ids': invoice_line_ids,
            })
            # sql = f"""update account_move set partner_id = {data.get('partner_id')} where id = {invoice_customer.id}"""
            # self._cr.execute(sql)
            # Vào sổ hóa đơn mua hàng
            invoice_customer.action_post()
            # data_stp_out.with_context({'skip_immediate': True}).button_validate()
            for st in data_all_picking:
                st_picking_in = self.env['stock.picking'].with_context({'skip_immediate': True}).create(data_all_picking[st])
                st_picking_in.action_set_quantities_to_reservation()
                st_picking_in.button_validate()
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
        stock_relationship = self.env['stock.picking'].search([('origin', '=', self.name),
                                                               ('state', '!=', 'done'),
                                                               ('picking_type_id.code', '=', 'incoming'),
                                                               ])
        if stock_relationship:
            for item in stock_relationship:
                item.write({
                    'state': 'cancel'
                })

    @api.model
    def get_import_templates(self):
        if self.env.context.get('default_is_inter_company'):
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/template_po_lien_cong_ty_ver2.0.xlsx?download=true'
            }]
        elif not self.env.context.get('default_is_inter_company') and self.env.context.get(
                'default_type_po_cost') == 'cost':
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/template_po_noi_dia_ver2.0.xlsx?download=true'
            }]
        elif not self.env.context.get('default_is_inter_company') and self.env.context.get(
                'default_type_po_cost') == 'tax':
            return [{
                'label': _('Tải xuống mẫu đơn mua hàng'),
                'template': '/forlife_purchase/static/src/xlsx/template_po_nhap_khau_ver2.0.xlsx?download=true'
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
        default['purchase_type'] = self.purchase_type
        return super().copy(default)

    def action_view_invoice_normal_new(self):
        data_search = self.env['account.move'].search(
            [('purchase_order_product_id', 'in', self.ids), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'normal')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search)],
        }

    def action_view_invoice_labor_new(self):
        data_search = self.env['account.move'].search(
            [('purchase_order_product_id', 'in', self.ids), ('move_type', '=', 'in_invoice'),
             ('select_type_inv', '=', 'labor')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search)],
        }

    def action_view_invoice_expense_new(self):
        for rec in self:
            data_search = self.env['account.move'].search(
                [('purchase_order_product_id', 'in', self.ids), ('move_type', '=', 'in_invoice'),
                 ('select_type_inv', '=', 'expense')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search)],
        }

    def action_view_invoice_service_new(self):
        data_search = self.env['account.move'].search(
            [('purchase_order_product_id', 'in', self.ids), ('move_type', '=', 'in_invoice'), ('select_type_inv', '=', 'service')]).ids
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', data_search)],
        }

    def create_invoice_normal_yes_return(self, order, line, wave_item):
        data_line = {
            'ware_id': wave_item.id,
            'ware_name': wave_item.picking_id.name,
            'po_id': line.id,
            'product_id': line.product_id.id,
            # 'sequence': sequence,
            'price_subtotal': line.price_subtotal,
            'promotions': line.free_good,
            'exchange_quantity': wave_item.quantity_change,
            'purchase_uom': line.purchase_uom.id,
            # 'quantity': wave_item.qty_done - x_return.qty_done,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            'request_code': line.request_purchases,
            'quantity_purchased': wave_item.quantity_purchase_done,
            'discount_percent': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax * (
                    wave_item.qty_done / line.product_qty),
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'occasion_code_id': wave_item.occasion_code_id.id,
            'work_order': wave_item.work_production.id,
            'account_analytic_id': wave_item.account_analytic_id.id,
            'import_tax': line.import_tax,
            # 'tax_amount': line.tax_amount,
            'special_consumption_tax': line.special_consumption_tax,
            'vat_tax': line.vat_tax,
        }
        return data_line

    def _prepare_invoice_normal(self, order, line):
        data_line = {
            # 'ware_id': move_line_id.id,
            # 'ware_name': move_line_id.picking_id.name,
            'po_id': line.id,
            'product_id': line.product_id.id,
            'price_subtotal': line.price_subtotal,
            'promotions': line.free_good,
            'exchange_quantity': line.exchange_quantity,
            'purchase_uom': line.purchase_uom.id,
            # 'quantity': wave_item.qty_done,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            'request_code': line.request_purchases,
            'quantity_purchased': line.purchase_quantity,
            'discount_percent': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax * (line.qty_received / line.product_qty),
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'occasion_code_id': line.occasion_code_id.id if line.occasion_code_id else False,
            'work_order': line.production_id.id if line.production_id else False,
            'account_analytic_id': line.account_analytic_id.id if line.account_analytic_id else False,
            'import_tax': line.import_tax,
            'special_consumption_tax': line.special_consumption_tax,
            'vat_tax': line.vat_tax,
        }
        return data_line

    def create_invoice_expense_no_return(self, order, nine, line, cp, wave_item, x_return):
        cp += ((line.total_vnd_amount / sum(order.order_line.mapped('total_vnd_amount'))) * (
                    (wave_item.qty_done - x_return.qty_done) / line.purchase_quantity)) * nine.vnd_amount
        data_line = {
            'ware_id': wave_item.id,
            'ware_name': wave_item.picking_id.name,
            'po_id': line.id,
            'product_id': nine.product_id.id,
            'description': nine.product_id.name,
            # 'sequence': sequence,
            'quantity': 1,
            'price_unit': cp,
            'occasion_code_id': wave_item.occasion_code_id.id,
            'work_order': wave_item.work_production.id,
            'account_analytic_id': wave_item.account_analytic_id.id,
            'import_tax': line.import_tax,
            # 'tax_amount': line.tax_amount,
            'special_consumption_tax': line.special_consumption_tax,
            # 'special_consumption_tax_amount': line.special_consumption_tax_amount,
            'vat_tax': line.vat_tax,
            # 'vat_tax_amount': line.vat_tax_amount,
        }
        return data_line

    def _prepare_invoice_expense(self, order, cost_line, po_line, cp):
        # if cost_line.actual_cost <= 0:
        #     return {}
        amount_rate = po_line.total_vnd_amount / sum(order.order_line.mapped('total_vnd_amount'))
        cp += ((amount_rate * cost_line.vnd_amount) / po_line.product_qty) * po_line.qty_received
        if po_line.currency_id != po_line.company_currency:
            rates = po_line.currency_id._get_rates(po_line.company_id, order.date_order)
            cp = cp * rates.get(po_line.currency_id.id)

        data_line = {
            'po_id': po_line.id,
            'product_id': po_line.product_id.id,
            'product_expense_origin_id': cost_line.product_id.id,
            'description': po_line.product_id.name,
            'account_id': cost_line.product_id.categ_id.property_stock_account_input_categ_id.id,
            'name': cost_line. product_id.name,
            'quantity': 1,
            'price_unit': cp,
            'occasion_code_id': po_line.occasion_code_id.id if po_line.occasion_code_id else False,
            'work_order': po_line.production_id.id if po_line.production_id else False,
            'account_analytic_id': po_line.account_analytic_id.id if po_line.account_analytic_id else False,
            'import_tax': po_line.import_tax,
        }
        return data_line

    def create_invoice_labor_no_return(self, line_id, material_line, wave_item, x_return):
        data_line = {
            'ware_id': wave_item.id,
            'ware_name': wave_item.picking_id.name,
            'po_id': line_id.id,
            'product_id': material_line.product_id.id,
            'description': material_line.product_id.name,
            'quantity': 1,
            # 'sequence': sequence,
            'price_unit': material_line.price_unit * (
                        (wave_item.qty_done - x_return.qty_done) / line_id.purchase_quantity),
            'occasion_code_id': wave_item.occasion_code_id.id,
            'work_order': wave_item.work_production.id,
            'account_analytic_id': wave_item.account_analytic_id.id,
            'import_tax': line_id.import_tax,
            # 'tax_amount': line.tax_amount,
            'special_consumption_tax': line_id.special_consumption_tax,
            # 'special_consumption_tax_amount': line.special_consumption_tax_amount,
            'vat_tax': line_id.vat_tax,
            # 'vat_tax_amount': line.vat_tax_amount,
        }
        return data_line

    def create_invoice_labor(self, line_id, material_line, wave_item):
        data_line = {
            'ware_id': wave_item.id,
            'ware_name': wave_item.picking_id.name,
            'po_id': line_id.id,
            'product_id': material_line.product_id.id,
            'description': material_line.product_id.name,
            'quantity': 1,
            # 'sequence': sequence,
            'price_unit': material_line.price_unit * (wave_item.qty_done / line_id.purchase_quantity),
            'occasion_code_id': wave_item.occasion_code_id.id,
            'work_order': wave_item.work_production.id,
            'account_analytic_id': wave_item.account_analytic_id.id,
            'import_tax': line_id.import_tax,
            # 'tax_amount': line.tax_amount,
            'special_consumption_tax': line_id.special_consumption_tax,
            # 'special_consumption_tax_amount': line.special_consumption_tax_amount,
            'vat_tax': line_id.vat_tax,
            # 'vat_tax_amount': line.vat_tax_amount,
        }
        return data_line

    def create_invoice_service_and_asset(self, order, line, wave):
        data_line = {
            'po_id': line.id,
            'product_id': line.product_id.id,
            # 'sequence': sequence,
            'promotions': line.free_good,
            'exchange_quantity': line.exchange_quantity,
            'purchase_uom': line.purchase_uom.id,
            'quantity': line.product_qty,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            # 'event_id': line.event_id.id,
            'request_code': line.request_purchases,
            'quantity_purchased': line.purchase_quantity,
            'discount_percent': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit - sum(wave.mapped('price_unit')),
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'occasion_code_id': line.occasion_code_id.id,
            'work_order': line.production_id.id,
            'account_analytic_id': line.account_analytic_id.id,
        }
        return data_line

    def create_invoice_service_and_asset_not_get_mode(self, order, line):
        data_line = {
            'po_id': line.id,
            'product_id': line.product_id.id,
            # 'sequence': sequence,
            'price_subtotal': line.price_subtotal,
            'promotions': line.free_good,
            'exchange_quantity': line.exchange_quantity,
            'purchase_uom': line.purchase_uom.id,
            'quantity': line.product_qty,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            # 'event_id': line.event_id.id,
            'request_code': line.request_purchases,
            'quantity_purchased': line.purchase_quantity,
            'discount_percent': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'occasion_code_id': line.occasion_code_id.id,
            'work_order': line.production_id.id,
            'account_analytic_id': line.account_analytic_id.id,
        }
        return data_line

    def create_invoice_normal_control_len(self, order, line,
                                          matching_item, quantity):
        data_line = {
            'ware_id': matching_item.id,
            'ware_name': matching_item.picking_id.name,
            'po_id': line.id,
            'product_id': matching_item.product_id.id,
            'promotions': line.free_good,
            'exchange_quantity': matching_item.quantity_change,
            'purchase_uom': line.purchase_uom.id,
            'quantity': quantity,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            'request_code': line.request_purchases,
            'quantity_purchased': 0,
            'discount_percent': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax,
            'product_uom_id': matching_item.product_uom_id.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * order.exchange_rate,
            'occasion_code_id': matching_item.occasion_code_id.id,
            'work_order': matching_item.production_id.id,
            'account_analytic_id': matching_item.account_analytic_id.id,
        }
        return data_line

    def _prepare_invoice_labor(self, order, labor_cost_id):
        pol_id = labor_cost_id.purchase_order_line_id
        data = {
            'po_id': pol_id.id,
            'product_id': pol_id.product_id.id,
            'product_expense_origin_id': labor_cost_id.product_id.id,
            'description': pol_id.product_id.name,
            'account_id': labor_cost_id.product_id.categ_id.property_stock_account_input_categ_id.id,
            'name': labor_cost_id.product_id.name,
            'quantity': 1,
            'price_unit': labor_cost_id.price_unit * (pol_id.qty_received / pol_id.product_qty),
            'occasion_code_id': pol_id.occasion_code_id.id if pol_id.occasion_code_id else False,
            'work_order': pol_id.production_id.id if pol_id.production_id else False,
            'account_analytic_id': pol_id.account_analytic_id.id if pol_id.account_analytic_id else False,
            'import_tax': pol_id.import_tax,
            'special_consumption_tax': pol_id.special_consumption_tax,
            'vat_tax': pol_id.vat_tax,
        }
        return data

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
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            sequence = 10
            for order in self:
                if order.custom_state != 'approved':
                    raise UserError(_('Tạo hóa đơn không hợp lệ!'))
                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                purchase_type = order.purchase_type
                if order.select_type_inv in ('expense', 'labor'):
                    purchase_type = 'service'
                invoice_vals.update({
                    'purchase_type': purchase_type,
                    'invoice_date': datetime.now(),
                    'exchange_rate': order.exchange_rate,
                    'currency_id': order.currency_id.id
                })
                # Invoice line values (keep only necessary sections).

                if order.select_type_inv == 'labor':
                    if order.order_line_production_order:
                        if order.order_line_production_order.purchase_order_line_material_line_ids:
                            pol_material_line_ids = order.order_line_production_order.purchase_order_line_material_line_ids
                            labor_cost_ids = pol_material_line_ids.filtered(lambda x: x.product_id.x_type_cost_product == 'labor_costs')
                            for labor_cost_id in labor_cost_ids:
                                pol_id = labor_cost_id.purchase_order_line_id
                                data_line = self._prepare_invoice_labor(order, labor_cost_id)
                                if pol_id.display_type == 'line_section':
                                    pending_section = pol_id
                                    continue
                                if pending_section:
                                    line_vals = pending_section._prepare_account_move_line()
                                    line_vals.update(data_line)
                                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                    sequence += 1
                                    pending_section = None
                                line_vals = pol_id._prepare_account_move_line()
                                line_vals.update(data_line)
                                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                sequence += 1
                            invoice_vals_list.append(invoice_vals)


                    # domain_labor = [('origin', '=', order.name), ('state', '=', 'done'),
                    #                 ('labor_check', '=', True), ('picking_type_id.code', '=', 'incoming')]
                    # picking_labor_in = self.env['stock.picking'].search(domain_labor + [('x_is_check_return', '=', False)])
                    # picking_labor_in_return = self.env['stock.picking'].search(domain_labor + [('x_is_check_return', '=', True)])
                    # if order.order_line_production_order:
                    #     material_lines = self.env['purchase.order.line.material.line'].search(
                    #         [('purchase_order_line_id', 'in', order.order_line_production_order.mapped('id'))])
                    #     for line in order.order_line:
                    #         for line_id in order.order_line_production_order:
                    #             material = material_lines.filtered(lambda m: m.purchase_order_line_id.id == line_id.id)
                    #             if not order.is_return:
                    #                 wave = picking_labor_in.move_line_ids_without_package.filtered(
                    #                     lambda w: w.move_id.purchase_line_id.id == line_id.id
                    #                               and w.product_id.id == line_id.product_id.id
                    #                               and w.picking_type_id.code == 'incoming'
                    #                               and w.picking_id.x_is_check_return == False)
                    #             else:
                    #                 wave = picking_labor_in.move_line_ids_without_package.filtered(lambda w: w.move_id.purchase_line_id.id == line_id.id
                    #                                                                                 and w.product_id.id == line_id.product_id.id
                    #                                                                                 and w.picking_id.x_is_check_return == False)
                    #             for material_line in material:
                    #                 if material_line.product_id.product_tmpl_id.x_type_cost_product == 'labor_costs' and picking_labor_in:
                    #                     for wave_item in wave:
                    #                         purchase_return = picking_labor_in_return.move_line_ids_without_package.filtered(
                    #                             lambda r: r.move_id.purchase_line_id.id == wave_item.move_id.purchase_line_id.id
                    #                                       and r.product_id.id == wave_item.product_id.id
                    #                                       and r.picking_id.relation_return == wave_item.picking_id.name
                    #                                       and r.picking_id.x_is_check_return == True)
                    #                         if purchase_return:
                    #                             for x_return in purchase_return:
                    #                                 if wave_item.picking_id.name == x_return.picking_id.relation_return:
                    #                                     data_line = self.create_invoice_labor_no_return(line_id, material_line, wave_item, x_return)
                    #                         else:
                    #                             data_line = self.create_invoice_labor(line_id, material_line, wave_item)
                    #                         if line.display_type == 'line_section':
                    #                             pending_section = line
                    #                             continue
                    #                         if pending_section:
                    #                             line_vals = pending_section._prepare_account_move_line()
                    #                             line_vals.update(data_line)
                    #                             invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    #                             sequence += 1
                    #                             pending_section = None
                    #                         line_vals = line._prepare_account_move_line()
                    #                         line_vals.update(data_line)
                    #                         invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    #                         sequence += 1
                    #                     invoice_vals_list.append(invoice_vals)
                    else:
                        raise UserError(_('Đơn mua không có chi phí nhân công và npl!'))
                elif order.select_type_inv == 'expense':
                    domain_expense = [('origin', '=', order.name),
                                      ('state', '=', 'done'),
                                      ('expense_check', '=', True),
                                      ('picking_type_id.code', '=', 'incoming')
                                      ]
                    picking_expense_in = self.env['stock.picking'].search(domain_expense + [('x_is_check_return', '=', False)])
                    picking_expense_in_return = self.env['stock.picking'].search(domain_expense + [('x_is_check_return', '=', True)])

                    if order.cost_line:
                        for cost_line in order.cost_line:
                            # invoice_vals['invoice_line_ids'].append((0, 0, {
                            #     'product_id': cost.product_id.id,
                            #     'price_unit': cost.actual_cost,
                            #     'tax_ids': []
                            # }))
                            # sequence += 1
                            # invoice_vals_list.append(invoice_vals)
                            cp = 0
                            for line in order.order_line:
                                # if not order.is_return:
                                #     wave = picking_expense_in.move_line_ids_without_package.filtered(
                                #         lambda w: w.move_id.purchase_line_id.id == line.id
                                #                 and w.product_id.id == line.product_id.id
                                #                 and w.picking_id.state == 'done'
                                #                 and w.picking_type_id.code == 'incoming'
                                #                 and w.picking_id.x_is_check_return == False)
                                # else:
                                #     wave = picking_expense_in.move_line_ids_without_package.filtered(lambda w: w.move_id.purchase_line_id.id == line.id
                                #                                                                     and w.product_id.id == line.product_id.id
                                #                                                                     and w.picking_id.x_is_check_return == False)
                                #
                                # for wave_item in wave:
                                #     purchase_return = picking_expense_in_return.move_line_ids_without_package.filtered(
                                #         lambda r: r.move_id.purchase_line_id.id == wave_item.move_id.purchase_line_id.id
                                #                   and r.product_id.id == wave_item.product_id.id
                                #                   and r.picking_id.relation_return == wave_item.picking_id.name
                                #                   and r.picking_id.x_is_check_return == True)
                                #     if purchase_return:
                                #         for x_return in purchase_return:
                                #             if wave_item.picking_id.name == x_return.picking_id.relation_return:
                                #                 data_line = self.create_invoice_expense_no_return(order, nine, line, cp, wave_item, x_return)
                                #     else:
                                data_line = self._prepare_invoice_expense(order, cost_line, line, cp)
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

                            invoice_vals_list.append(invoice_vals)
                    else:
                        raise UserError(_('Đơn mua không có chi phí!'))
                else:
                    if self.purchase_type not in ('service', 'asset'):
                        domain_normal = [('purchase_id', '=', order.id),
                                         ('state', '=', 'done'),
                                         ('picking_type_id.code', '=', 'incoming')
                                         ]
                        domain_normal_out = [('purchase_id', '=', order.id),
                                         ('state', '=', 'done'),
                                         ('picking_type_id.code', '=', 'outgoing')
                                         ]
                        picking_in = self.env['stock.picking'].search(domain_normal + [('ware_check', '=', False)])
                        picking_in_return = self.env['stock.picking'].search(domain_normal_out + [('ware_check', '=', False)])
                        picking_in_true = self.env['stock.picking'].search(domain_normal + [('ware_check', '=', True)])
                        for line in order.order_line:
                            # nếu ko phải order return
                            # if not order.is_return:
                            #     wave = picking_in.move_line_ids_without_package.filtered(
                            #         lambda w: w.move_id.purchase_line_id.id == line.id
                            #                   and w.product_id.id == line.product_id.id
                            #                   and w.picking_type_id.code == 'incoming'
                            #                   and w.picking_id.x_is_check_return == False)
                            # else:
                            #     wave = picking_in.move_line_ids_without_package.filtered(lambda w: w.move_id.purchase_line_id.id == line.id
                            #                                                                     and w.product_id.id == line.product_id.id
                            #                                                                     and w.picking_id.x_is_check_return == False)
                            # if picking_in:
                            #     for wave_item in wave:
                            #
                            #         move_line_return_id = picking_in_return.move_line_ids_without_package.filtered(
                            #             lambda r: r.move_id.purchase_line_id.id == wave_item.move_id.purchase_line_id.id
                            #                       and r.product_id.id == wave_item.product_id.id
                            #                       and r.picking_id.relation_return == wave_item.picking_id.name
                            #                       and r.picking_id.x_is_check_return == True)
                            #         if move_line_return_id:
                            #             for x_return in move_line_return_id:
                            #                 if wave_item.picking_id.name == x_return.picking_id.relation_return:
                            #                     data_line = self.create_invoice_normal_yes_return(order, line, wave_item, x_return)
                            #         else:
                            data_line = self._prepare_invoice_normal(order, line)
                            if line.display_type == 'line_section':
                                pending_section = line
                                continue
                            if pending_section:
                                line_vals = pending_section._prepare_account_move_line()
                                line_vals.update(data_line)
                                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                                sequence += 1
                                pending_section = None
                            # wave_item.picking_id.ware_check = True
                            line_vals = line._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            sequence += 1
                            invoice_vals_list.append(invoice_vals)
                            # elif picking_in_true:
                            #     invoice_relationship = self.env['account.move.line'].search(
                            #         [('ware_id', '=', picking_in_true.move_line_ids_without_package.mapped('id'))])
                            #     for item in picking_in_true.move_line_ids_without_package:
                            #         invoice_l = invoice_relationship.filtered(lambda x: x.ware_id.id == item.id)
                            #         if invoice_l.purchase_line_id.id == line.id:
                            #             total_nine_quantity = 0
                            #             matching_item = item
                            #             for nine in invoice_relationship:
                            #                 total_nine_quantity += nine.quantity
                            #             quantity = matching_item.qty_done - total_nine_quantity
                            #             if quantity > 0:
                            #                 data_line = self.create_invoice_normal_control_len(order, line, matching_item, quantity)
                            #             else:
                            #                 raise ValidationError('Hóa đơn đã được khống chế số lượng theo số lượng phiếu nhập kho tương ứng')
                            #             if line.display_type == 'line_section':
                            #                 pending_section = line
                            #                 continue
                            #             if pending_section:
                            #                 line_vals = pending_section._prepare_account_move_line()
                            #                 line_vals.update(data_line)
                            #                 invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            #                 sequence += 1
                            #                 pending_section = None
                            #             line_vals = line._prepare_account_move_line()
                            #             line_vals.update(data_line)
                            #             invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            #             sequence += 1
                    else:
                        invoice_relationship = self.env['account.move'].search([('reference', '=', order.name),
                                                                                ('partner_id', '=', order.partner_id.id),
                                                                                ('purchase_type', '=', order.purchase_type)
                                                                                ])
                        if invoice_relationship:
                            if sum(invoice_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(
                                    order.order_line.mapped('price_subtotal')):
                                raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng!'))
                            else:
                                for line in order.order_line:
                                    wave = invoice_relationship.invoice_line_ids.filtered(lambda w: w.purchase_line_id.id ==
                                        line.id and w.product_id.id == line.product_id.id)
                                    data_line = self.create_invoice_service_and_asset(order, line, wave)
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
                                data_line = self.create_invoice_service_and_asset_not_get_mode(order, line)
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
                    # 'purchase_type': self.purchase_type if len(self) == 1 else 'product',
                    'reference': ', '.join(self.mapped('name')),
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'type_inv': self.type_po_cost,
                    'select_type_inv': self.select_type_inv,
                    'is_check_select_type_inv': True,
                    'trade_discount': self.trade_discount,
                    'total_trade_discount': self.total_trade_discount,
                    'x_tax': self.x_tax,
                    'x_amount_tax': self.x_amount_tax,
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
            for master in moves:
                master.purchase_order_product_id = [(6, 0, [self.id])]
                domain = [('origin', 'in', master.purchase_order_product_id.mapped('name')),
                          ('state', '=', 'done'),
                          ('x_is_check_return', '=', False),
                          ('picking_type_id.code', '=', 'incoming')
                          ]
                picking_expense_in = self.env['stock.picking'].search(domain + [('expense_check', '=', True)])
                picking_labor_in = self.env['stock.picking'].search(domain + [('labor_check', '=', True)])
                picking_normal_in = self.env['stock.picking'].search(domain + [('ware_check', '=', True)])
                if picking_expense_in:
                    master.receiving_warehouse_id = [(6, 0, picking_expense_in.ids)]
                if picking_labor_in:
                    master.receiving_warehouse_id = [(6, 0, picking_labor_in.ids)]
                if picking_normal_in:
                    master.receiving_warehouse_id = [(6, 0, picking_normal_in.ids)]
                if not picking_expense_in and not picking_labor_in and not picking_normal_in:
                    master.receiving_warehouse_id = [(6, 0, [])]

                products = []
                product_expenses = []
                for line in master.invoice_line_ids:
                    if line.product_id and line.move_id.purchase_type == 'product':
                        if line.product_id.property_account_expense_id:
                            account_id = line.product_id.property_account_expense_id.id
                        else:
                            account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                        line.account_id = account_id

                    if line.product_id and line.move_id.purchase_type == 'service' and line.move_id.is_trade_discount_move:
                        if line.product_id.property_account_expense_id:
                            line.account_id = line.product_id.property_account_expense_id.id

                    #   add product
                    if line.product_id not in products:
                        products.append(line.product_id)

                    if line.product_expense_origin_id not in product_expenses:
                        product_expenses.append(line.product_expense_origin_id)
                lst_sum = []
                for product in products:
                    sum_product_moves = moves.invoice_line_ids.filtered(lambda x: x.product_id == product)
                    item_vals = {
                        'product_id': product.id,
                        'description': product.name,
                        'uom_id': product.uom_id.id
                    }
                    lst_sum.append((0, 0, item_vals))

                master.write({
                    'sum_expense_labor_ids': lst_sum
                })
                lst_expense = []
                for product_expense in product_expenses:
                    sum_product_expense_moves = moves.invoice_line_ids.filtered(lambda x: x.product_expense_origin_id == product_expense)
                    item_vals = {
                        'product_id': product_expense.id,
                        'description': product_expense.name,
                        'uom_id': product_expense.uom_id.id,
                        'qty': 1,
                        'price_subtotal_back': sum([x.price_unit for x in sum_product_expense_moves])
                    }
                    lst_expense.append((0, 0, item_vals))

                master.write({
                    'account_expense_labor_detail_ids': lst_expense
                })


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
            return moves


    def create_multi_invoice_vendor(self):
        sequence = 10
        vals_all_invoice = {}
        reference = []
        for order in self:
            reference.append(order.name)
            ref_join = ', '.join(reference)
            if order.custom_state != 'approved':
                raise UserError(_('Tạo hóa đơn không hợp lệ cho đơn mua %s!') % ref_join)
            picking_expense_in = order.picking_ids.filtered(lambda x: x.state == 'done' and
                                                                      x.x_is_check_return == False and
                                                                      x.expense_check == True and
                                                                      x.picking_type_id.code == 'incoming')
            picking_in = order.picking_ids.filtered(lambda x: x.state == 'done' and
                                                              x.x_is_check_return == False and
                                                              x.picking_type_id.code == 'incoming')
            picking_labor_in = order.picking_ids.filtered(lambda x: x.state == 'done' and
                                                                    x.labor_check == True and
                                                                    x.x_is_check_return == False and
                                                                    x.picking_type_id.code == 'incoming')
            if order.purchase_type in ('service', 'asset'):
                invoice_relationship = self.env['account.move'].search([('reference', '=', order.name),
                                                                      ('partner_id', '=', order.partner_id.id)])
                for line in order.order_line:
                    if invoice_relationship:
                        if sum(invoice_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(
                                order.order_line.mapped('price_subtotal')):
                            raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng %s!') % order.name)
                        else:
                            wave = invoice_relationship.invoice_line_ids.filtered(lambda w: w.purchase_line_id.id == line.id and w.product_id.id == line.product_id.id)
                            data_line = self.create_invoice_service_and_asset(order, line, wave)
                    else:
                        data_line = self.create_invoice_service_and_asset_not_get_mode(order, line)
                    sequence += 1
                    key = order.purchase_type, order.partner_id.id, order.company_id.id
                    invoice_vals = order._prepare_invoice()
                    invoice_vals.update({'purchase_type': order.purchase_type,
                                         'invoice_date': datetime.now(),
                                         'exchange_rate': order.exchange_rate,
                                         'currency_id': order.currency_id.id,
                                         'reference': order.name,
                                         'type_inv': order.type_po_cost,
                                         'select_type_inv': order.select_type_inv,
                                         'is_check_select_type_inv': True,
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
            elif order.select_type_inv == 'normal':
                key = order.purchase_type, order.partner_id.id, order.company_id.id
                for line in order.order_line:
                    for wave_item in picking_in.move_line_ids_without_package:
                        if wave_item.move_id.purchase_line_id.id == line.id:
                            sequence += 1
                            data_line = self._prepare_invoice_normal(order, line, wave_item)
                            order = order.with_company(order.company_id)
                            line_vals = line._prepare_account_move_line()
                            line_vals.update(data_line)
                            invoice_vals = order._prepare_invoice()
                            invoice_vals.update({'purchase_type': order.purchase_type,
                                                 'invoice_date': datetime.now(),
                                                 'exchange_rate': order.exchange_rate,
                                                 'currency_id': order.currency_id.id,
                                                 'reference': order.name,
                                                 'type_inv': order.type_po_cost,
                                                 'select_type_inv': order.select_type_inv,
                                                 'is_check_select_type_inv': True,
                                                 'purchase_order_product_id': self.ids,
                                                 })
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            if vals_all_invoice.get(key):
                                vals_all_invoice.get(key)['invoice_line_ids'].append((0, 0, line_vals))
                            else:
                                vals_all_invoice.update({
                                    key: invoice_vals
                                })
            elif order.select_type_inv == 'expense':
                for nine in order.cost_line:
                    for line in order.order_line:
                        if order.cost_line:
                            cp = 0
                            for wave_item in picking_expense_in.move_line_ids_without_package:
                                if wave_item.move_id.purchase_line_id.id == line.id and wave_item.product_id.id == line.product_id.id and wave_item.picking_id.state == 'done' and wave_item.picking_type_id.code == 'incoming':
                                    data_line = self._prepare_invoice_expense(order, nine, line, cp, wave_item)
                        else:
                            raise UserError(_('Đơn mua có mã phiếu là %s chưa có chi phí!') % order.name)
                        sequence += 1
                        key = order.purchase_type, order.partner_id.id, order.company_id.id
                        invoice_vals = order._prepare_invoice()
                        invoice_vals.update({'purchase_type': order.purchase_type,
                                             'invoice_date': datetime.now(),
                                             'exchange_rate': order.exchange_rate,
                                             'currency_id': order.currency_id.id,
                                             'reference': order.name,
                                             'type_inv': order.type_po_cost,
                                             'select_type_inv': order.select_type_inv,
                                             'is_check_select_type_inv': True,
                                             'purchase_order_product_id': self.ids,
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
                material = self.env['purchase.order.line.material.line'].search(
                    [('purchase_order_line_id', '=', self.order_line_production_order.mapped('id'))])
                for line in order.order_line:
                    if self.order_line_production_order:
                        for nine in self.order_line_production_order:
                            for material_line in material:
                                if material_line.product_id.product_tmpl_id.x_type_cost_product == 'labor_costs' and picking_labor_in:
                                    for wave_item in picking_labor_in.move_line_ids_without_package:
                                        if wave_item.move_id.purchase_line_id.id == nine.id and wave_item.product_id.id == nine.product_id.id:
                                            data_line = self.create_invoice_labor(nine, material_line, wave_item)
                    else:
                        raise UserError(_('Đơn mua có mã phiếu là %s chưa có chi phí nhân công!') % ref_join)
                    sequence += 1
                    key = order.purchase_type, order.partner_id.id, order.company_id.id
                    invoice_vals = order._prepare_invoice()
                    invoice_vals.update({'purchase_type': order.purchase_type,
                                         'invoice_date': datetime.now(),
                                         'exchange_rate': order.exchange_rate,
                                         'currency_id': order.currency_id.id,
                                         'reference': order.name,
                                         'type_inv': order.type_po_cost,
                                         'select_type_inv': order.select_type_inv,
                                         'is_check_select_type_inv': True,
                                         'purchase_order_product_id': self.ids,
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
        for data in vals_all_invoice:
            move = moves.create(vals_all_invoice.get(data))
            for line in move.invoice_line_ids:
                if line.product_id and line.move_id.purchase_type == 'product':
                    account_id = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id
                    line.account_id = account_id
            for line in move:
                reference = []
                for nine in line.purchase_order_product_id:
                    reference.append(nine.name)
                    ref_join = ', '.join(reference)
                    line.reference = ref_join
                domain = [('origin', 'in', line.purchase_order_product_id.mapped('name')),
                          ('state', '=', 'done'),
                          ('x_is_check_return', '=', False),
                          ('picking_type_id.code', '=', 'incoming')
                          ]
                picking_expense_in = self.env['stock.picking'].search(domain + [('expense_check', '=', True)])
                picking_labor_in = self.env['stock.picking'].search(domain + [('labor_check', '=', True)])
                picking_normal_in = self.env['stock.picking'].search(domain + [('ware_check', '=', True)])
                if picking_expense_in:
                    line.receiving_warehouse_id = [(6, 0, picking_expense_in.ids)]
                elif picking_labor_in:
                    line.receiving_warehouse_id = [(6, 0, picking_labor_in.ids)]
                elif picking_normal_in:
                    line.receiving_warehouse_id = [(6, 0, picking_normal_in.ids)]
                else:
                    line.receiving_warehouse_id = [(6, 0, [])]
            move.filtered(
                lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
            return move

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
        cost_line_vals = []
        for cl in self.cost_line:
            move_done = sum(self.order_line.move_ids.filtered(lambda x:x.state == 'done').mapped('quantity_done'))
            total_qty = sum(self.order_line.mapped('product_qty'))
            data = cl.copy_data({'vnd_amount': move_done/total_qty * cl.vnd_amount, 'cost_line_origin': cl.id})[0]
            if 'purchase_order_id' in data:
                del data['purchase_order_id']
            if 'actual_cost' in data:
                del data['actual_cost']
            cost_line_vals.append((0, 0, data))
        values.update({
            'trade_discount': self.trade_discount,
            'total_trade_discount': self.total_trade_discount,
            'cost_line': cost_line_vals
        })
        product_discount_tax = self.env.ref('forlife_purchase.product_discount_tax')
        if not product_discount_tax:
            product_discount_tax = self.env['product.product'].search([('name', '=', 'Chiết khấu tổng đơn'), ('detailed_type', '=', 'service')], limit=1)

        if self.order_line.filtered(lambda x: x.product_id.id == product_discount_tax.id):
            values.update({
                'move_type': 'in_refund',
                'is_trade_discount_move': True,
                'ref': f"{self.name} Chiết khấu tổng đơn",
                'invoice_description': f"Hóa đơn chiết khấu tổng đơn",
                'is_check_invoice_tnk': True if self.env.ref('forlife_pos_app_member.partner_group_1') else False,
                'e_in_check': self.id,
            })
        return values

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        if "import_file" in self.env.context:
            for rec in self:
                if not rec.partner_id:
                    raise ValidationError('Thiếu giá trị bắt buộc cho trường Nhà cung cấp!')

    @api.constrains('purchase_type')
    def _constrains_purchase_type(self):
        for rec in self:
            if not rec.purchase_type:
                raise ValidationError('Thiếu giá trị bắt buộc cho trường Loại mua hàng!')

    @api.constrains('currency_id')
    def _constrains_currency_id(self):
        for rec in self:
            if not rec.currency_id:
                raise ValidationError('Thiếu giá trị bắt buộc cho trường Tiền tệ!')

    @api.constrains('exchange_rate')
    def _constrains_exchange_rate(self):
        for rec in self:
            if not rec.exchange_rate:
                raise ValidationError('Thiếu giá trị bắt buộc cho trường Tỷ giá!')

    @api.constrains('date_order')
    def _constrains_date_order(self):
        for rec in self:
            if not rec.date_order:
                raise ValidationError('Thiếu giá trị bắt buộc cho trường Ngày đặt hàng!')

    @api.constrains('receive_date')
    def _constrains_receive_date(self):
        for rec in self:
            if not rec.receive_date:
                raise ValidationError('Thiếu giá trị bắt buộc cho trường Ngày nhận!')

    @api.model
    def load(self, fields, data):
        if "import_file" and 'default_is_inter_company' in self.env.context:
            line_number = 1
            default_type = None
            for mouse in data:
                line_number += 1
                if line_number == 2:
                    default_type = mouse[fields.index('purchase_type')]
                ### check type po and line po import
                if self.env.context['default_is_inter_company']:
                    if default_type == 'Hàng hóa':
                        if fields.index('order_line/purchase_uom') and not mouse[fields.index('order_line/purchase_uom')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn vị mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/purchase_quantity') and not mouse[fields.index('order_line/purchase_quantity')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng đặt mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/exchange_quantity') and not mouse[fields.index('order_line/exchange_quantity')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Tỷ lệ quy đổi ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                    elif default_type == 'Dịch vụ':
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/product_qty') and not mouse[fields.index('order_line/product_qty')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                    elif default_type == 'Tài sản':
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/product_qty') and not mouse[fields.index('order_line/product_qty')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                else:
                    if default_type == 'Hàng hóa':
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/purchase_quantity') and not mouse[fields.index('order_line/purchase_quantity')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng đặt mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/purchase_uom') and not mouse[fields.index('order_line/purchase_uom')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn vị mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/exchange_quantity') and not mouse[fields.index('order_line/exchange_quantity')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Tỷ lệ quy đổi ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/vendor_price_import') and not mouse[fields.index('order_line/vendor_price_import')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Giá của nhà cung cấp ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/location_id') and not mouse[fields.index('order_line/location_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Địa điểm kho ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('cost_line/product_id') and mouse[fields.index('cost_line/product_id')] and not mouse[fields.index('cost_line/currency_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Tiền tệ ở tab chi phí ở dòng - {}".format(line_number)))
                    elif default_type == 'Dịch vụ':
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/product_qty') and not mouse[fields.index('order_line/product_qty')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/purchase_uom') and not mouse[fields.index('order_line/purchase_uom')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn vị mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/price_unit') and not mouse[fields.index('order_line/price_unit')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn giá ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                    elif default_type == 'Tài sản':
                        if fields.index('order_line/product_id') and not mouse[fields.index('order_line/product_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Mã sản phẩm ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/product_qty') and not mouse[fields.index('order_line/product_qty')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Số lượng ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/purchase_uom') and not mouse[fields.index('order_line/purchase_uom')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn vị mua ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/price_unit') and not mouse[fields.index('order_line/price_unit')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Đơn giá ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('order_line/receive_date') and not mouse[fields.index('order_line/receive_date')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Ngày nhận ở tab chi tiết đơn hàng ở dòng - {}".format(line_number)))
                        if fields.index('cost_line/product_id') and mouse[fields.index('cost_line/product_id')] and not mouse[fields.index('cost_line/currency_id')]:
                            raise ValidationError(_("Thiếu giá trị bắt buộc cho trường Tiền tệ ở tab chi phí ở dòng - {}".format(line_number)))
        return super(PurchaseOrder, self).load(fields, data)

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
                'price_subtotal': amount_untaxed if amount_untaxed else line.price_subtotal,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    product_qty = fields.Float(string='Quantity', digits=(16, 0), required=False,
                               compute='_compute_product_qty', store=True, readonly=False, copy=True)
    asset_code = fields.Many2one('assets.assets', string='Asset code')
    asset_name = fields.Char(string='Asset name')
    purchase_quantity = fields.Float('Purchase Quantity', digits='Product Unit of Measure')
    purchase_uom = fields.Many2one('uom.uom', string='Purchase UOM')
    exchange_quantity = fields.Float('Exchange Quantity', default=1.0)
    # line_sub_total = fields.Monetary(compute='_get_line_subtotal', string='Line Subtotal', readonly=True, store=True)
    discount_percent = fields.Float(string='Discount (%)', digits='Discount', default=0.0, compute='_compute_free_good', store=1, readonly=False)
    discount = fields.Float(string='Discount (Amount)', digits='Discount', default=0.0, compute='_compute_free_good', store=1, readonly=False)

    @api.constrains('discount_percent')
    def _constrains_discount_percent_and_discount(self):
        for rec in self:
            if rec.discount_percent < 0 or rec.discount_percent > 100:
                raise UserError(_('Bạn không thể nhập chiết khấu % nhỏ hơn 0 hoặc lớn hơn 100!'))


    free_good = fields.Boolean(string='Free Goods')
    warehouses_id = fields.Many2one('stock.warehouse', string="Whs", check_company=True)
    location_id = fields.Many2one('stock.location', string="Địa điểm kho", check_company=True)
    production_id = fields.Many2one('forlife.production', string='Production Order Code', domain=[('state', '=', 'approved'), ('status', '=', 'in_approved')], ondelete='restrict')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Account Analytic Account')
    request_purchases = fields.Char(string='Phiếu yêu cầu')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    vendor_price = fields.Float(string='Giá nhà cung cấp', compute='compute_vendor_price_ncc', store=1)
    vendor_price_import = fields.Float(string='Giá của nhà cung cấp')
    readonly_discount = fields.Boolean(default=False, compute='_compute_free_good', store=1)
    readonly_discount_percent = fields.Boolean(default=False, compute='_compute_free_good', store=1)
    is_passersby = fields.Boolean(related='order_id.is_passersby', store=1)
    supplier_id = fields.Many2one('res.partner', related='order_id.partner_id')
    receive_date = fields.Datetime(string='Date receive')
    tolerance = fields.Float(related='product_id.tolerance', string='Dung sai')
    qty_returned = fields.Integer(string="Returned Qty", compute="_compute_qty_returned", store=True)
    billed = fields.Float(string='Đã có hóa đơn', compute='compute_billed')
    received = fields.Integer(string='Đã nhận', compute='compute_received')
    occasion_code_id = fields.Many2one('occasion.code', string="Mã vụ việc")
    description = fields.Char(related='product_id.name', store=True, required=False, string='Mô tả')
    # Phục vụ import
    taxes_id = fields.Many2many('account.tax', string='Thuế(%)',
                                domain=['|', ('active', '=', False), ('active', '=', True)])
    domain_uom = fields.Char(string='Lọc đơn vị', compute='compute_domain_uom')
    is_red_color = fields.Boolean(compute='compute_vendor_price_ncc', store=1)
    name = fields.Char(related='product_id.name', store=True, required=False)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', store=True, required=False)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    is_change_vendor = fields.Integer()
    total_vnd_amount = fields.Monetary('Tổng tiền VND',
                                    compute='_compute_total_vnd_amount',
                                    store=1)
    total_vnd_exchange = fields.Monetary('Thành tiền VND',
                                    compute='_compute_total_vnd_amount',
                                    store=1)
    total_vnd_exchange_import = fields.Float('Thành tiền VND của sản phẩm')
    import_tax = fields.Float(string='% Thuế nhập khẩu')
    tax_amount = fields.Float(string='Thuế nhập khẩu',
                              compute='_compute_tax_amount',
                              store=1)
    tax_amount_import = fields.Float('Thuế nhập khẩu của sản phẩm')
    special_consumption_tax = fields.Float(string='% Thuế tiêu thụ đặc biệt')
    special_consumption_tax_amount = fields.Float(string='Thuế tiêu thụ đặc biệt',
                                                  compute='_compute_special_consumption_tax_amount',
                                                  store=1)
    special_consumption_tax_amount_import = fields.Float('Thuế TTĐB của sản phẩm')
    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='Thuế GTGT',
                                  compute='_compute_vat_tax_amount',
                                  store=1)
    vat_tax_amount_import = fields.Float('Thuế GTGT của sản phẩm')

    total_tax_amount = fields.Float(string='Tổng tiền thuế',
                                    compute='_compute_total_tax_amount',
                                    store=1)
    total_product = fields.Float(string='Tổng giá trị tiền hàng', compute='_compute_total_product', store=1)
    before_tax = fields.Float(string='Chi phí trước tính thuế', compute='_compute_before_tax', store=1)
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)', compute='_compute_after_tax', store=1)
    company_currency = fields.Many2one('res.currency', string='Tiền tệ VND', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('total_vnd_exchange_import',
                    'total_vnd_amount', 'before_tax',
                    'order_id.is_inter_company','order_id')
    def _constrain_total_vnd_exchange_import(self):
        line_number = 1
        for rec in self:
            line_number += 1
            if rec.order_id.type_po_cost == 'tax' and rec.order_id.is_inter_company == False and rec.before_tax and rec.total_vnd_exchange_import and rec.total_vnd_amount:
                if rec.total_vnd_exchange_import != (rec.total_vnd_amount + rec.before_tax):
                    raise ValidationError(_("Tiền sản phẩm trước thuế %s (*Gợi ý: Tiền ở tab thuế nhập khẩu) != Thành tiền VND của sản phẩm cộng với chi phí trước thuế (%s + %s) ở dòng - {}".format(line_number)) %(rec.total_vnd_exchange_import, rec.total_vnd_amount, rec.before_tax))

    @api.onchange('vat_tax')
    def _onchange_vat_tax(self):
        self.vat_tax_amount = (self.total_vnd_exchange + self.tax_amount + self.special_consumption_tax_amount) * self.vat_tax / 100

    @api.onchange('import_tax')
    def _onchange_import_tax(self):
        self.tax_amount = self.total_vnd_exchange * self.import_tax / 100

    @api.onchange('special_consumption_tax')
    def _onchange_special_consumption_tax(self):
        self.special_consumption_tax_amount = (self.total_vnd_exchange + self.tax_amount) * self.special_consumption_tax / 100

    @api.constrains('import_tax', 'special_consumption_tax', 'vat_tax')
    def constrains_per(self):
        for item in self:
            if item.import_tax < 0:
                raise ValidationError('% thuế nhập khẩu phải >= 0 !')
            if item.special_consumption_tax < 0:
                raise ValidationError('% thuế tiêu thụ đặc biệt phải >= 0 !')
            if item.vat_tax < 0:
                raise ValidationError('% thuế GTGT >= 0 !')

    @api.depends('total_vnd_exchange', 'import_tax', 'tax_amount_import')
    def _compute_tax_amount(self):
        for rec in self:
            if not rec.tax_amount_import:
                rec.tax_amount = rec.total_vnd_exchange * rec.import_tax / 100
            else:
                rec.tax_amount = rec.tax_amount_import

    @api.depends('tax_amount', 'special_consumption_tax', 'special_consumption_tax_amount_import', 'import_tax')
    def _compute_special_consumption_tax_amount(self):
        for rec in self:
            if not rec.special_consumption_tax_amount_import:
                rec.special_consumption_tax_amount = (rec.total_vnd_exchange + rec.tax_amount) * rec.special_consumption_tax / 100
            else:
                rec.special_consumption_tax_amount = rec.special_consumption_tax_amount_import

    @api.depends('special_consumption_tax_amount', 'vat_tax', 'vat_tax_amount_import')
    def _compute_vat_tax_amount(self):
        for rec in self:
            if not rec.vat_tax_amount_import:
                rec.vat_tax_amount = (rec.total_vnd_exchange + rec.tax_amount + rec.special_consumption_tax_amount) * rec.vat_tax / 100
            else:
                rec.vat_tax_amount = rec.vat_tax_amount_import

    @api.depends('vat_tax_amount')
    def _compute_total_tax_amount(self):
        for rec in self:
            if not rec.total_tax_amount:
                rec.total_tax_amount = rec.tax_amount + rec.special_consumption_tax_amount + rec.vat_tax_amount


    @api.depends('price_subtotal', 'order_id.exchange_rate', 'order_id', 'total_vnd_exchange_import', 'before_tax')
    def _compute_total_vnd_amount(self):
        for rec in self:
            if not rec.total_vnd_exchange_import:
                if rec.price_subtotal and rec.order_id.exchange_rate:
                    rec.total_vnd_amount = rec.total_vnd_exchange = round(rec.price_subtotal * rec.order_id.exchange_rate)
            else:
                rec.total_vnd_amount = round(rec.price_subtotal * rec.order_id.exchange_rate)
                rec.total_vnd_exchange = rec.total_vnd_exchange_import

    @api.onchange('product_id', 'is_change_vendor')
    def onchange_product_id(self):
        if self.product_id and self.product_id.uom_po_id:
            self.purchase_uom = self.product_id.uom_po_id.id
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

    @api.onchange('asset_code')
    def onchange_asset_code(self):
        if self.asset_code:
            if not self.get_product_code():
                self.product_id = None
                self.name = None
                return {'domain': {'product_id': [('id', '=', 0)],
                                   'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                         ('company_id', '=', self.order_id.company_id.id)]
                                   }}
        else:
            return {'domain': {'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                     ('company_id', '=', self.order_id.company_id.id)]}}

    def get_product_code(self):
        account = self.asset_code.asset_account.id
        product_categ_id = self.env['product.category'].search([('property_account_expense_categ_id', '=', account)])
        if not product_categ_id:
            raise UserError(_('Không có nhóm sản phẩm nào cấu hình Tài khoản chi phí là %s' % self.asset_code.asset_account.code))
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

    @api.constrains('taxes_id')
    def constrains_taxes_id(self):
        for item in self:
            if len(item.taxes_id) > 1:
                raise ValidationError('Bạn chỉ chọn được 1 giá trị thuế')

    @api.constrains('purchase_uom')
    def _constrains_purchase_uom(self):
        for rec in self:
            if not rec.purchase_uom and not rec.order_id.is_inter_company:
                raise ValidationError(_('Đơn vị mua của sản phẩm %s chưa được chọn!') % rec.product_id.name)

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
                acc_move = self.env['account.move'].search([('purchase_order_product_id', 'in', item.order_id.ids), ('state', '=', 'posted'), ('select_type_inv', '=', 'normal')])
                if acc_move:
                    acc_move_line = self.env['account.move.line'].search(
                        [('move_id', 'in', acc_move.ids), ('product_id', '=', item.product_id.id), ('po_id', '=', str(item.id))]).mapped('quantity')
                    item.billed = sum(acc_move_line)
                else:
                    item.billed = False
            else:
                item.billed = False

    @api.depends('exchange_quantity', 'product_qty', 'product_id', 'purchase_uom', 'order_id.purchase_type', 'vendor_price_import',
                 'order_id.partner_id', 'order_id.partner_id.is_passersby', 'order_id', 'order_id.currency_id',
                 'free_good')
    def compute_vendor_price_ncc(self):
        today = datetime.now().date()
        for rec in self:
            if not (rec.product_id and rec.order_id.partner_id and rec.purchase_uom and rec.order_id.currency_id) or rec.order_id.partner_id.is_passersby:
                if rec.vendor_price_import:
                    if not rec.free_good:
                        rec.vendor_price = rec.vendor_price_import
                    else:
                        rec.vendor_price = 0
                    rec.is_red_color = False
                    continue
            data = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id),
                ('partner_id', '=', rec.order_id.partner_id.id),
                ('currency_id', '=', rec.order_id.currency_id.id),
                ('amount_conversion', '=', rec.exchange_quantity),
                ('product_uom', '=', rec.purchase_uom.id),
                ('date_start', '<=', today),
                ('date_end', '>=', today)
            ])
            rec.is_red_color = True if rec.exchange_quantity not in data.mapped('amount_conversion') else False
            if rec.product_id and rec.order_id.partner_id and rec.purchase_uom and rec.order_id.currency_id and not rec.is_red_color and not rec.order_id.partner_id.is_passersby:
                closest_quantity = None  # Khởi tạo giá trị biến tạm
                for line in data:
                    if rec.product_qty and rec.product_qty >= line.min_qty:
                        ### closest_quantity chỉ được cập nhật khi rec.product_qty lớn hơn giá trị hiện tại của line.min_qty
                        if closest_quantity is None or line.min_qty > closest_quantity:
                            closest_quantity = line.min_qty
                            if not rec.free_good:
                                rec.vendor_price = line.price
                            else:
                                rec.vendor_price = 0
                            rec.exchange_quantity = line.amount_conversion

    # discount
    @api.depends("free_good")
    def _compute_free_good(self):
        for rec in self:
            if rec.free_good:
                rec.write({'discount': 0,
                           'discount_percent': 0,
                           'readonly_discount_percent': True,
                           'readonly_discount': True,
                           })
            else:
                rec.write({'readonly_discount_percent': False,
                           'readonly_discount': False,
                           })


    @api.onchange("discount_percent", 'vendor_price')
    def _onchange_discount_percent(self):
        if not self.readonly_discount_percent:
            if self.discount_percent:
                self.discount = self.discount_percent * self.price_unit * self.product_qty * 0.01
                self.readonly_discount = True
            elif self.discount_percent == 0:
                self.discount = 0
                self.readonly_discount = False
            else:
                self.readonly_discount = False

    @api.onchange("discount", 'vendor_price')
    def _onchange_discount(self):
        if not self.readonly_discount:
            if self.discount and self.price_unit > 0 and self.product_qty > 0:
                self.discount_percent = (self.discount / (self.price_unit * self.product_qty * 0.01))
                self.readonly_discount_percent = True
            elif self.discount == 0:
                self.discount_percent = 0
                self.readonly_discount_percent = False
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
    @api.depends('purchase_quantity', 'purchase_uom', 'product_qty',
                 'exchange_quantity', 'product_uom', 'vendor_price',
                 'order_id.purchase_type', 'free_good')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if line.free_good:
                line.price_unit = 0
            if line.vendor_price:
                if line.exchange_quantity != 0:
                    line.price_unit = line.vendor_price / line.exchange_quantity
                else:
                    line.price_unit = line.vendor_price
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

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

    @api.depends('purchase_quantity', 'exchange_quantity', 'order_id.purchase_type')
    def _compute_product_qty(self):
        for line in self:
            if line.purchase_quantity:
                line.product_qty = line.purchase_quantity * line.exchange_quantity

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

    def _prepare_account_move_line(self):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line()
        if vals and vals.get('display_type') == 'product':
            # quantity = self.qty_received - self.qty_returned - self.billed
            quantity = self.qty_to_invoice
            vals.update({
                'exchange_quantity': self.exchange_quantity,
                'quantity': quantity,
            })
        if self.asset_code:
            vals.update({
                'asset_code': self.asset_code.id,
                'asset_name': self.asset_name
            })
        return vals

    @api.depends('order_id.cost_line.is_check_pre_tax_costs', 'order_id.order_line')
    def _compute_before_tax(self):
        for rec in self:
            cost_line_true = rec.order_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            for line in rec.order_id.order_line:
                total_cost_true = 0
                if cost_line_true and line.total_vnd_amount > 0:
                    for item in cost_line_true:
                        before_tax = line.total_vnd_amount / sum(rec.order_id.order_line.mapped('total_vnd_amount')) * item.vnd_amount
                        total_cost_true += before_tax
                        line.before_tax = total_cost_true
                    line.total_vnd_exchange = line.total_vnd_amount + line.before_tax
                else:
                    line.before_tax = 0
                    if line.before_tax != 0:
                        line.total_vnd_exchange = line.total_vnd_amount + line.before_tax
                    else:
                        line.total_vnd_exchange = line.total_vnd_amount

    @api.depends('order_id.cost_line.is_check_pre_tax_costs', 'order_id.exchange_rate_line_ids')
    def _compute_after_tax(self):
        for rec in self:
            cost_line_false = rec.order_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            for line in rec.order_id.order_line:
                total_cost = 0
                sum_vnd_amount = sum(rec.order_id.exchange_rate_line_ids.mapped('total_vnd_exchange'))
                sum_tnk = sum(rec.order_id.exchange_rate_line_ids.mapped('tax_amount'))
                sum_db = sum(rec.order_id.exchange_rate_line_ids.mapped('special_consumption_tax_amount'))
                if cost_line_false and line.total_vnd_exchange > 0:
                    for item in cost_line_false:
                        total_cost += (line.total_vnd_exchange + line.tax_amount + line.special_consumption_tax_amount) / (sum_vnd_amount + sum_tnk + sum_db) * item.vnd_amount
                        line.after_tax = total_cost
                else:
                    line.after_tax = 0

    @api.depends('total_vnd_amount', 'before_tax', 'tax_amount', 'special_consumption_tax_amount', 'after_tax')
    def _compute_total_product(self):
        for record in self:
            record.total_product = record.total_vnd_amount + record.before_tax + record.tax_amount + record.special_consumption_tax_amount + record.after_tax

    def _handle_stock_move_price_unit(self):
        price_unit = self.price_unit
        if self.discount:
            price_unit -= self.discount / self.product_qty
        elif self.discount_percent:
            price_unit -= (price_unit * self.discount_percent / 100)
        return price_unit

    def _get_stock_move_price_unit(self):
        self.ensure_one()
        order = self.order_id
        price_unit = self._handle_stock_move_price_unit()
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        if self.taxes_id:
            qty = self.product_qty or 1
            price_unit = self.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=self.order_id.currency_id, quantity=qty, product=self.product_id,
                partner=self.order_id.partner_id
            )['total_void']
            price_unit = price_unit / qty
        if self.product_uom.id != self.product_id.uom_id.id:
            price_unit *= self.product_uom.factor / self.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(),
                round=False)
        return float_round(price_unit, precision_digits=price_unit_prec)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_ncc = fields.Boolean('From Ncc')
    reference = fields.Char(string='Tài liệu')
    is_trade_discount_move = fields.Boolean('Is trade discount move', default=False)

    def action_post(self):
        for rec in self:
            if rec.purchase_order_product_id:
                for item in rec.purchase_order_product_id:
                    item.write({
                        'invoice_status_fake': 'invoiced',
                    })
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': True
                })
        res = super(AccountMove, self).action_post()
        return res

    def button_cancel(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).button_cancel()

    def unlink(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).unlink()

    def button_draft(self):
        for rec in self:
            if rec.receiving_warehouse_id:
                rec.receiving_warehouse_id.write({
                    'ware_check': False
                })
        return super(AccountMove, self).button_draft()

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def check_quant_goods_import(self, po):
        self.ensure_one()
        material_line_ids = po.order_line_production_order.purchase_order_line_material_line_ids
        material_product_ids = material_line_ids.filtered(lambda x: not x.product_id.x_type_cost_product and x.product_id.detailed_type == 'product').product_id.ids
        if not material_product_ids:
            return
        if self.state == 'done':
            product_ids = [
                (quant['product_id'][0], quant['quantity'] or 0)
                for quant in self.env['stock.quant'].read_group(
                    domain=[('location_id', '=', po.location_export_material_id.id),  ('product_id', 'in', material_product_ids)],
                    fields=['quantity'],
                    groupby='product_id')
            ]
            product_not_quant = self.env['product.product'].sudo().search([
                '|', ('id', 'in', [product[0] for product in product_ids if product[1] <= 0]),
                '&', ('id', 'not in', [product[0] for product in product_ids]), ('id', 'in', material_product_ids)
            ])
            if product_not_quant:
                raise ValidationError('Những nguyên phụ liệu sau không đủ tồn kho: \n%s' % '\n'.join(product.name for product in product_not_quant))


    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self._context.get('endloop'):
            return True
        for record in self:
            po = record.purchase_id
            if not po:
                continue
            if po.is_inter_company == False and not po.is_return and not record.move_ids[0]._is_purchase_return():
                if record.state == 'done':
                    ## check npl tồn:
                    self.check_quant_goods_import(po)
                    po.write({
                        'inventory_status': 'done',
                        'invoice_status_fake': 'to invoice',
                    })
                    _context = {
                        'pk_no_input_warehouse': False,
                    }
                    if po.type_po_cost == 'tax':
                        # tạo bút toán định giá tồn kho với thuế nhập khẩu và thuế đặc biệt
                        if po and po.exchange_rate_line_ids:
                            move_import_tax_values = self.prepare_move_svl_value_with_tax_po(po, 'import') # thuế nhập khẩu
                            move_special_tax_values = self.prepare_move_svl_value_with_tax_po(po, 'special') # thuế tiêu thụ đặc biệt
                            move_values = move_import_tax_values + move_special_tax_values
                            moves = self.env['account.move'].create(move_values)
                            if moves:
                                moves._post()
                        if po.cost_line:
                            self.create_expense_entries(po)
                            '''
                            cp = self.create_invoice_po_cost(po, record)
                            '''
                    elif po.type_po_cost == 'cost':
                        self.create_expense_entries(po)
                        '''
                        cp = self.create_invoice_po_cost(po, record)
                        '''
                    # Tạo nhập khác xuất khác khi nhập kho
                    if po.order_line_production_order and not po.is_inter_company:
                        npl = self.create_invoice_npl(po, record)
                    for rec in record.move_ids_without_package:
                        if rec.work_production:
                            quantity = self.env['quantity.production.order'].search(
                                [('product_id', '=', rec.product_id.id),
                                 ('location_id', '=', rec.picking_id.location_dest_id.id),
                                 ('production_id', '=', rec.work_production.id)])
                            if quantity:
                                quantity.write({
                                    'quantity': quantity.quantity + rec.quantity_done
                                })
                            else:
                                self.env['quantity.production.order'].create({
                                    'product_id': rec.product_id.id,
                                    'location_id': rec.picking_id.location_dest_id.id,
                                    'production_id': rec.work_production.id,
                                    'quantity': rec.quantity_done
                                })
                    account_move = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
                    account_move.update({
                        'currency_id': po.currency_id.id,
                        'exchange_rate': po.exchange_rate
                    })
        return res

    def prepare_move_svl_value_with_tax_po(self, po, tax_type):
        if not po.exchange_rate_line_ids or len(po.exchange_rate_line_ids) <= 0:
            return []
        move_values = []
        for line in po.exchange_rate_line_ids:
            amount = line.tax_amount if tax_type != 'special' else line.special_consumption_tax_amount
            qty_po_origin = line.product_qty
            move = self.env['stock.move'].search([('purchase_line_id', '=', line.id), ('picking_id', '=', self.id)])
            qty_po_done = sum(move.mapped('quantity_done'))
            if tax_type != 'special':
                product_tax = self.env.ref('forlife_purchase.product_import_tax_default')
            else:
                product_tax = self.env.ref('forlife_purchase.product_excise_tax_default')
            move_value = {
                'ref': f"{self.name} - {line.product_id.name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'journal_id': self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id,
                'exchange_rate': po.exchange_rate,
                'date': datetime.now(),
                'invoice_payment_term_id': po.payment_term_id.id,
                'invoice_date_due': po.date_planned,
                'restrict_mode_hash_table': False,
            }
            svl_values = []
            move_lines = [(0, 0, {
                'sequence': 1,
                'account_id': product_tax.categ_id.property_stock_account_input_categ_id.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'text_check_cp_normal': line.product_id.name,
                'credit': (amount / qty_po_origin) * qty_po_done,
                'debit': 0
            })]
            if move.product_id.type in ('product', 'consu'):
                svl_values.append((0, 0, {
                    'value': (amount / qty_po_origin) * qty_po_done,
                    'unit_cost': amount / qty_po_origin,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': f"{self.name} - {line.product_id.name}",
                    'product_id': move.product_id.id,
                    'company_id': self.env.company.id,
                    'stock_move_id': move.id
                }))
                move_lines += [(0, 0, {
                    'sequence': 2,
                    'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                    'product_id': move.product_id.id,
                    'name': move.product_id.name,
                    'text_check_cp_normal': line.product_id.name,
                    'credit': 0.0,
                    'debit': (amount / qty_po_origin) * qty_po_done,
                })]

            move_value.update({
                'stock_valuation_layer_ids': svl_values,
                'line_ids': move_lines
            })

            move_values.append(move_value)

        return move_values

    def view_move_tax_entry(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all")
        domain = ['|', ('move_id', 'in', (self.move_ids).stock_valuation_layer_ids.mapped('account_move_id').ids), ('move_id.stock_move_id', 'in', self.move_ids.ids)]
        return dict(action, domain=domain)

    def create_expense_entries(self, po):
        self.ensure_one()
        results = self.env['account.move']
        if self.state != 'done' or not po:
            return results
        entries_values = []
        for move in self.move_ids:
            if move.product_id.type not in ('product', 'consu'):
                continue
            product_po = po.order_line.filtered(lambda x: x.product_id == move.product_id)
            po_total_qty = sum(product_po.mapped('product_qty'))
            amount_rate = sum(product_po.mapped('total_vnd_amount')) / sum(po.order_line.mapped('total_vnd_amount'))
            for expense in po.cost_line:
                expense_vnd_amount = expense.vnd_amount * amount_rate
                sp_total_qty = move.quantity_done

                if sp_total_qty == 0:
                    continue
                entries_values += [{
                    'ref': f"{self.name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_cost',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.utcnow(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'restrict_mode_hash_table': False,
                    'stock_valuation_layer_ids': [(0, 0, {
                        'value': expense_vnd_amount / po_total_qty * move.quantity_done,
                        'unit_cost': expense_vnd_amount / po_total_qty,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {expense.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    })],
                    'invoice_line_ids': [(0, 0, {
                        'sequence': 1,
                        'account_id': expense.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'product_id': move.product_id.id,
                        'name': expense.product_id.name,
                        'text_check_cp_normal': expense.product_id.name,
                        'credit': expense_vnd_amount / po_total_qty * sp_total_qty,
                        'debit': 0
                    }),
                    (0, 0, {
                         'sequence': 2,
                         'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                         'product_id': move.product_id.id,
                         'name': move.product_id.name,
                         'text_check_cp_normal': move.product_id.name,
                         'credit': 0,
                         'debit': expense_vnd_amount / po_total_qty * move.quantity_done
                    })],
                }]
                for value in entries_values:
                    debit = 0.0
                    for line in value['invoice_line_ids'][1:]:
                        if debit:
                            line[-1]['debit'] += debit
                            debit = 0.0
                        else:
                            debit = line[-1]['debit'] - round(line[-1]['debit'])
                            line[-1]['debit'] = round(line[-1]['debit'])
        results = results.create(entries_values)
        results._post()
        return results

    # Xử lý nhập kho sinh bút toán ở tab chi phí po theo số lượng nhập kho
    def create_invoice_po_cost(self, po, record):
        data_in_line = po.order_line
        data_ex_line = po.exchange_rate_line_ids
        data_co_line = po.cost_line
        data_st_line = record.move_ids_without_package
        list_cp_after_tax = []
        list_money = []
        tax_amount = []
        special_amount = []
        total_vnd_exchange = []
        if record.state == 'done':
            for po_l, pk_l, ex_l in zip(data_in_line, data_st_line, data_ex_line):
                if pk_l.picking_id.state == 'done':
                    if pk_l.quantity_done * po_l.price_unit != 0:
                        list_money.append((pk_l.quantity_done/po_l.product_qty * po_l.total_vnd_amount))
                    if ex_l.tax_amount:
                        tax_amount.append(ex_l.tax_amount)
                    if ex_l.special_consumption_tax_amount:
                        special_amount.append(ex_l.special_consumption_tax_amount)
                    if ex_l.total_vnd_exchange:
                        total_vnd_exchange.append(ex_l.total_vnd_exchange)
            total_money = sum(list_money)
            total_tax_amount = sum(tax_amount)
            total_special_amount = sum(special_amount)
            total_vnd_exchange = sum(total_vnd_exchange)
            for item, exchange, total, pk_l in zip(data_in_line, data_ex_line, list_money, data_st_line):
                if item.product_id.categ_id and item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(('Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm %s!') % item.product_id.name)
                for rec in data_co_line:
                    if rec.product_id.categ_id and rec.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                        account_acc = rec.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id
                    else:
                        raise ValidationError(('Bạn chưa cấu hình nhập kho trong danh mục sản phẩm của %s!') % rec.product_id.name)
                    if rec.vnd_amount:
                        if not rec.is_check_pre_tax_costs:
                            values = (((exchange.total_vnd_exchange + exchange.tax_amount + exchange.special_consumption_tax_amount) * pk_l.quantity_done / item.product_qty) / ((
                                                              total_vnd_exchange + total_tax_amount + total_special_amount) * pk_l.quantity_done / item.product_qty)) * rec.vnd_amount * pk_l.quantity_done / item.product_qty
                            debit_cp = (0, 0, {
                                'sequence': 1,
                                'account_id': account_1561,
                                'product_id': item.product_id.id,
                                'name': item.product_id.name,
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
                                'name': item.product_id.name,
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
                if merged_records_list_cp:
                    entry_cp = self.env['account.move'].create({
                        'ref': f"{record.name} - {rec.product_id.name}",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'x_entry_types': 'entry_cost',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_cp,
                        'restrict_mode_hash_table': False
                    })
                    entry_cp._post()

    # Xử lý nhập kho sinh bút toán ở tab thuế nhập khẩu po theo số lượng nhập kho
    def create_invoice_po_tax(self, po, record):
        list_nk = []
        list_db = []
        if record.state == 'done':
            for ex_l, pk_l in zip(po.exchange_rate_line_ids, record.move_ids_without_package):
                if ex_l.product_id.categ_id and ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(_('Bạn chưa cấu hình tài khoản định giá tồn kho của sản phẩm %s trong danh mục của sản phẩm đó!') % ex_l.product_id.name)
                if ex_l.product_qty <= 0 and pk_l.quantity_done <= 0:
                    raise ValidationError('Số lượng của sản phẩm hay số lương hoàn thành khi nhập kho phải lớn hơn 0')
                if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế nhập khẩu'")
                if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế tiêu thụ đặc biệt'")
                if ex_l.tax_amount:
                    debit_nk = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'name': ex_l.product_id.name,
                        'debit': (pk_l.quantity_done / ex_l.product_qty * ex_l.tax_amount),
                        'credit': 0,
                    })
                    credit_nk = (0, 0, {
                        'sequence': 99991,
                        'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id.id,
                        'name': self.env.ref('forlife_purchase.product_import_tax_default').name,
                        'debit': 0,
                        'credit': (pk_l.quantity_done / ex_l.product_qty * ex_l.tax_amount),
                    })
                    lines_nk = [debit_nk, credit_nk]
                    list_nk.extend(lines_nk)
                if ex_l.special_consumption_tax_amount:
                    debit_db = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'name': ex_l.product_id.name,
                        'debit': (pk_l.quantity_done / ex_l.product_qty * ex_l.special_consumption_tax_amount),
                        'credit': 0,
                    })
                    credit_db = (0, 0, {
                        'sequence': 99991,
                        'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id.id,
                        'name': self.env.ref('forlife_purchase.product_excise_tax_default').name,
                        'debit': 0,
                        'credit': (pk_l.quantity_done / ex_l.product_qty * ex_l.special_consumption_tax_amount),
                    })
                    lines_db = [debit_db, credit_db]
                    list_db.extend(lines_db)
            merged_records_tnk = {}
            merged_records_db = {}
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
            if merged_records_list_tnk:
                entry_nk = self.env['account.move'].create({
                    'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_import_tax_default').name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_import_tax',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': merged_records_list_tnk,
                    'restrict_mode_hash_table': False
                })
                entry_nk._post()

            if merged_records_list_db:
                entry_db = self.env['account.move'].create({
                    'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_excise_tax_default').name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_special_consumption_tax',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': merged_records_list_db,
                    'restrict_mode_hash_table': False
                })
                entry_db._post()

    # Xử lý nhập kho sinh bút toán ở tab npl po theo số lượng nhập kho + sinh bút toán cho chi phí nhân công nội địa
    def create_invoice_npl(self, po, record):
        list_npls = []
        list_allowcation_npls = []
        list_line_xk = []
        cost_labor_internal_costs = []
        if record.state == 'done':
            move = False
            ### Tìm bản ghi Xuât Nguyên Phụ Liệu
            export_production_order = self.env['stock.location'].search([('company_id', '=', self.env.company.id),
                                                                         ('code', '=', 'X1201')
                                                                         ], limit=1)
            if not export_production_order.x_property_valuation_in_account_id:
                raise ValidationError('Bạn chưa có hoặc chưa cấu hình tài khoản trong lý do xuất nguyên phụ liệu \n Gợi ý: Tạo lý do trong cấu hình Lý do nhập khác và xuất khác có mã: X1201')
            else:
                if not export_production_order.reason_type_id:
                    raise ValidationError('Bạn chưa cấu hình loại lý do cho lý do nhập khác có mã: X1201')
                account_export_production_order = export_production_order.x_property_valuation_in_account_id
            for item, r in zip(po.order_line_production_order, record.move_ids_without_package):
                move = self.env['stock.move'].search(
                    [('purchase_line_id', '=', item.id), ('picking_id', '=', self.id)])
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
                        if material_line.price_unit > 0:
                            # pbo = material_line.price_unit * r.quantity_done/item.product_qty
                            pbo = material_line.price_unit * r.quantity_done * material_line.production_line_product_qty / material_line.production_order_product_qty
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
                        list_line_xk.append((0, 0, {
                            'product_id': material_line.product_id.id,
                            'product_uom': material_line.uom.id,
                            'price_unit': material_line.price_unit,
                            'location_id': po.location_export_material_id.id,
                            'location_dest_id': export_production_order.id,
                            'product_uom_qty': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'quantity_done': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'amount_total': material_line.price_unit * material_line.product_qty,
                            # 'reason_type_id': reason_type_6.id,
                            'reason_id': export_production_order.id,
                        }))
                        #tạo bút toán npl ở bên bút toán sinh với khi nhập kho khác với phiếu xuất npl
                        if item.product_id.id == material_line.purchase_order_line_id.product_id.id:
                            if material_line.product_id.standard_price > 0:
                                debit_npl = (0, 0, {
                                    'sequence': 9,
                                    'account_id': account_export_production_order.id,
                                    'name': account_export_production_order.name,
                                    'debit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                    'credit': 0,
                                })
                                credit_npl = (0, 0, {
                                    'sequence': 99991,
                                    'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id,
                                    'name': material_line.product_id.name,
                                    'debit': 0,
                                    'credit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                })
                                lines_npl = [debit_npl, credit_npl]
                                list_npls.extend(lines_npl)

                                #xử lý phân bổ nguyên vật liệu
                                debit_allowcation_npl = (0, 0, {
                                    'sequence': 1,
                                    'account_id': account_1561,
                                    'name': item.product_id.name,
                                    'debit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                    'credit': 0,
                                })

                                credit_allowcation_npl = (0, 0, {
                                    'sequence': 2,
                                    'account_id': account_export_production_order.id,
                                    'name': account_export_production_order.name,
                                    'debit': 0,
                                    'credit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                })
                                list_allowcation_npls.extend([debit_allowcation_npl, credit_allowcation_npl])

                if debit_cost > 0:
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


                    qty_po_done = sum(move.mapped('quantity_done'))
                    svl_values = []
                    svl_values.append((0, 0, {
                        'value': debit_cost,
                        'unit_cost': debit_cost / qty_po_done,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {item.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    }))
                    entry_cp = self.env['account.move'].create({
                        'ref': f"{record.name} - Chi phí nhân công thuê ngoài/nội bộ - {target_items}",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'x_entry_types': 'entry_cost_labor',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': invoice_line_ids,
                        'restrict_mode_hash_table': False,
                        'stock_valuation_layer_ids': svl_values
                    })
                    entry_cp._post()


            if list_npls:
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
                        'x_entry_types': 'entry_material',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_npl,
                        'restrict_mode_hash_table': False
                    })
                    entry_npls._post()
                    if record.state == 'done':
                        master_xk = self.create_xk_picking(po, record, list_line_xk, export_production_order, entry_npls)

            if list_allowcation_npls:
                merged_records_allowcation_npl = {}
                total_npl_amount = 0
                for allowcation_npl in list_allowcation_npls:
                    key = (
                    allowcation_npl[2]['account_id'], allowcation_npl[2]['name'], allowcation_npl[2]['sequence'])
                    if key in merged_records_allowcation_npl:
                        merged_records_allowcation_npl[key]['debit'] += allowcation_npl[2]['debit']
                        merged_records_allowcation_npl[key]['credit'] += allowcation_npl[2]['credit']
                    else:
                        merged_records_allowcation_npl[key] = {
                            'sequence': allowcation_npl[2]['sequence'],
                            'account_id': allowcation_npl[2]['account_id'],
                            'name': allowcation_npl[2]['name'],
                            'debit': allowcation_npl[2]['debit'],
                            'credit': allowcation_npl[2]['credit'],
                        }
                    total_npl_amount += allowcation_npl[2]['debit']
                merged_records_list_allowcation_npl = [(0, 0, record) for record in
                                                       merged_records_allowcation_npl.values()]
                if merged_records_list_allowcation_npl:
                    qty_po_done = sum(move.mapped('quantity_done'))
                    svl_allowcation_values = []
                    svl_allowcation_values.append((0, 0, {
                        'value': total_npl_amount,
                        'unit_cost': total_npl_amount / qty_po_done,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {item.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    }))
                    entry_allowcation_npls = self.env['account.move'].create({
                        'ref': f"{record.name} - Phân bổ nguyên phụ liệu",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        # 'x_entry_types': 'entry_material',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_allowcation_npl,
                        'restrict_mode_hash_table': False,
                        'stock_valuation_layer_ids': svl_allowcation_values
                    })
                    entry_allowcation_npls._post()

    ###tự động tạo phiếu xuất khác và hoàn thành khi nhập kho hoàn thành
    def create_xk_picking(self, po, record, list_line_xk, export_production_order, account_move=None):
        company_id = self.env.company.id
        picking_type_out = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', company_id)], limit=1)
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'location_id': po.location_export_material_id.id,
            # 'reason_type_id': reason_type_6.id,
            'location_dest_id': export_production_order.id,
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

class AccountTax(models.Model):
    _inherit = 'account.tax'
    _rec_names_search = ['code', 'name']

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _rec_names_search = ['name']
