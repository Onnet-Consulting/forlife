from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby, float_round
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import json


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _get_department_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.department_default_id

    def _get_team_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.team_default_id

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
    partner_id = fields.Many2one('res.partner', string='Nhà cung cấp', required=True, states=READONLY_STATES,
        change_default=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="You can find a vendor by its Name, TIN, Email or Internal Reference."
    )
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', compute='_compute_active_manual_currency_rate', store=1)
    production_id = fields.Many2one('forlife.production', string='Production Order', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], copy=False)
    custom_state = fields.Selection(default='draft', string="Status",
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('approved', 'Approved'),
            ('reject', 'Reject'),
            ('cancel', 'Cancel'),
            ('close', 'Close'),
        ])
    select_type_inv = fields.Selection(copy=False, string="Loại hóa đơn", required=True,
        selection=[
            ('expense', 'Hóa đơn chi phí mua hàng'),
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
    occasion_code_id = fields.Many2one('occasion.code', string="Mã vụ việc", copy=False)
    account_analytic_id = fields.Many2one('account.analytic.account', copy=False, string="Trung tâm chi phí")
    is_purchase_request = fields.Boolean(default=False, copy=False)
    is_check_readonly_partner_id = fields.Boolean(copy=False)
    is_check_readonly_purchase_type = fields.Boolean(copy=False)
    source_document = fields.Char(string="Source Document", copy=False)
    receive_date = fields.Datetime(string='Receive Date')
    note = fields.Char('Note')
    source_location_id = fields.Many2one('stock.location', string="Địa điểm nguồn")
    trade_discount = fields.Float(string='Chiết khấu thương mại(%)')
    total_trade_discount = fields.Float(string='Tổng chiết khấu thương mại')
    trade_tax_id = fields.Many2one(comodel_name='account.tax', string='Thuế VAT cùa chiết khấu(%)', domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]")
    x_tax = fields.Float(string='Thuế VAT cùa chiết khấu(%)')
    x_amount_tax = fields.Float(string='Tiền VAT của chiết khấu', compute='compute_x_amount_tax', store=1, readonly=False)
    total_trade_discounted = fields.Float(string='Tổng chiết khấu thương mại đã lên hóa đơn', compute='compute_total_trade_discounted')
    location_export_material_id = fields.Many2one('stock.location', string='Địa điểm xuất NPL')
    count_invoice_inter_company_ncc = fields.Integer(compute='compute_count_invoice_inter_company_ncc')
    count_invoice_inter_normal_fix = fields.Integer(compute='compute_count_invoice_inter_normal_fix')
    count_invoice_inter_expense_fix = fields.Integer(compute='compute_count_invoice_inter_expense_fix')
    count_invoice_inter_labor_fix = fields.Integer(compute='compute_count_invoice_inter_labor_fix')
    count_invoice_inter_company_customer = fields.Integer(compute='compute_count_invoice_inter_company_customer')
    count_delivery_inter_company = fields.Integer(compute='compute_count_delivery_inter_company')
    count_delivery_import_inter_company = fields.Integer(compute='compute_count_delivery_import_inter_company')
    cost_total = fields.Float(string='Tổng chi phí', compute='compute_cost_total', store=1)
    is_done_picking = fields.Boolean(default=False, compute='compute_is_done_picking')
    department_id = fields.Many2one('hr.department', string='Department', default=_get_department_default)
    team_id = fields.Many2one('hr.team', string='Team', default=_get_team_default)
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
    payment_term_id = fields.Many2one('account.payment.term', 'Chính sách thanh toán', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_company_id = fields.Many2one(comodel_name='res.company', compute='_compute_partner_company_id', index=True, store=True)
    date_planned = fields.Datetime(
        string='Expected Arrival', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")

    date_planned_import = fields.Datetime('Hạn xử lý')
    count_stock = fields.Integer(compute="compute_count_stock", copy=False)

    def compute_total_trade_discounted(self):
        for r in self:
            move_ids = r.order_line.invoice_lines.move_id.filtered(lambda x: x.state == 'posted')
            r.total_trade_discounted = sum(move_ids.mapped('total_trade_discount'))

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

    @api.onchange('trade_tax_id')
    def onchange_trade_tax_id(self):
        if self.trade_tax_id:
            self.x_tax = self.trade_tax_id.amount
        else:
            self.x_tax = 0

    @api.onchange('partner_id')
    def onchange_vendor_code(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id

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
            if self.partner_id and self.order_line and self.currency_id and not self.partner_id.is_passersby:
                date_now = datetime.now().date()
                domain = [
                    '|', ('product_id', 'in', self.order_line.product_id.ids),
                    ('product_tmpl_id', '=', self.order_line.product_id.product_tmpl_id.ids),
                    ('company_id', '=', self.company_id.id),
                    ('partner_id', '=', self.partner_id.id),
                    ('date_start', '<=', date_now),
                    ('date_end', '>=', date_now),
                    ('currency_id', '=', self.currency_id.id)
                ]
                product_supplierinfo_ids = self.env['product.supplierinfo'].search(domain)

                for line in self.order_line.filtered(lambda x: not x.free_good):
                    supplier_ids = product_supplierinfo_ids.filtered(lambda x: x.product_id.id == line.product_id.id or x.product_tmpl_id.id == line.product_id.product_tmpl_id.id)
                    if supplier_ids:
                        supplier_id = supplier_ids.sorted('price')[:1]
                        vendor_price = supplier_id.price if supplier_id.price else 0
                        exchange_quantity = supplier_id.amount_conversion if supplier_id.amount_conversion else 1
                        line.write({
                            'purchase_uom': supplier_id.product_uom.id,
                            'vendor_price': vendor_price,
                            'exchange_quantity': exchange_quantity,
                            'purchase_quantity': line.product_qty / exchange_quantity,
                            'price_unit': vendor_price / exchange_quantity
                        })

        if self.partner_id and self.sudo().source_location_id.company_id and self.env['res.company'].sudo().search([
            ('partner_id', '=', self.partner_id.id),
            ('id', '!=', self.sudo().source_location_id.company_id.id)
        ]):
            self.source_location_id = None

        # Do something with res
        return res

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
            record.is_done_picking = True if record.picking_ids.filtered(lambda x: x.state == 'done') else False

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

            # Validate trường hợp k có Sản phẩm hoặc tài khoản kế toán ở sản phẩm trong tab Chi phí
            for cost_line_id in record.cost_line:
                if not cost_line_id.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm %s" % cost_line_id.product_id.display_name)

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
        company_id = self.env['res.company'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)
        all_tax_ids = self.env['account.tax'].sudo().search([('type_tax_use', '=', 'sale'), ('company_id', '=', company_id.id)])
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
                'x_location_id': self.source_location_id.id if self.purchase_type == 'product' else False,
                'tax_id': [(6, 0, tax_ids)],
            }))

        # Tìm trung tâm chi phí có cùng mã
        account_analytic_id = False
        if self.account_analytic_id:
            account_analytic_id = self.env['account.analytic.account'].sudo().search([('code', '=', self.account_analytic_id.code), ('company_id', '=', company_id.id)], limit=1)

        occasion_code_id = False
        if self.occasion_code_id:
            occasion_code_id = self.env['occasion.code'].sudo().search([('code', '=', self.occasion_code_id.code), ('company_id', '=', company_id.id)], limit=1)

        sale_order_vals = {
            'company_id': company_id.id,
            'origin': self.name,
            'partner_id': self.company_id.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'date_order': self.date_order,
            'warehouse_id': self.source_location_id[0].warehouse_id.id if self.purchase_type == 'product' else self.sudo().env.user.with_company(company_id.id)._get_default_warehouse_id().id,
            'x_location_id': self.source_location_id.id if self.purchase_type == 'product' else False,
            'x_sale_type': self.purchase_type,
            'x_manufacture_order_code_id': self.production_id.id or False,
            'x_account_analytic_id': account_analytic_id.id if account_analytic_id else False,
            'x_occasion_code_id': occasion_code_id.id if occasion_code_id else False,
            'order_line': sale_order_lines
        }
        sale_id = self.env['sale.order'].sudo().create(sale_order_vals)
        return sale_id

    def action_approved(self):
        # self.check_purchase_tool_and_equipment()
        for record in self:
            if not record.is_inter_company:
                record.button_confirm()
                record.picking_ids.picking_type_id.write({
                    'show_operations': True
                })
                record.write({'custom_state': 'approved'})
            else:
                if not record.is_return:
                    record.action_approve_inter_company()
                else:
                    record.action_approve_inter_company_return()

                return True

    def action_approve_inter_company(self):
        self.sudo().with_context(inter_company=True)
        self.button_confirm()
        if self.purchase_type == 'product':
            self.validate_inter_purchase_order()
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
                    invoice.x_root = 'other'
                    invoice.action_post()
            else:
                raise UserError('Phiếu nhập kho chưa được hoàn thành, vui lòng kiểm tra lại!')
        else:
            self.write({
                'select_type_inv': 'normal',
                'custom_state': 'approved',
                'inventory_status': 'done',
            })
            invoice = self.action_create_invoice()
            invoice.x_root = 'other'
            invoice.action_post()

        sale_id = self.sudo()._create_sale_order_another_company()
        sale_id.action_create_picking()
        if self.purchase_type == 'product':
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
        else:
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

    def action_reject(self):
        for record in self:
            record.write({'custom_state': 'reject'})

    def action_cancel(self):
        super(PurchaseOrder, self).button_cancel()
        for record in self:
            record.write({'custom_state': 'cancel'})

    def action_close(self):
        self.button_cancel()
        self.write({'custom_state': 'close'})

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
            if rec.company_id or rec.currency_id and rec.company_id.currency_id != rec.currency_id:
                rec.active_manual_currency_rate = True
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
        if self.company_id or self.currency_id and self.company_id.currency_id != self.currency_id:
            self.active_manual_currency_rate = True
        else:
            self.active_manual_currency_rate = False

    @api.model_create_multi
    def create(self, vals):
        purchases = super(PurchaseOrder, self).create(vals)
        for purchase_id in purchases.filtered(lambda x: not x.is_inter_company):
            if not purchase_id.is_check_line_material_line and purchase_id.purchase_type == 'product' and not purchase_id.location_export_material_id:
                message = 'Địa điểm nhập NPL không thể thiếu, vui lòng kiểm tra lại!' if purchase_id.is_return else 'Địa điểm xuất NPL không thể thiếu, vui lòng kiểm tra lại!'
                raise ValidationError(message)
        return purchases

    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
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
        move_ids = self.env['account.move'].search([
            ('purchase_order_product_id', 'in', self.ids),
            ('move_type', '=', 'in_invoice'),
            ('select_type_inv', '=', 'normal')]
        )
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids.ids)],
        }

    def action_view_invoice_labor_new(self):
        move_ids = self.env['account.move'].search([
            ('purchase_order_product_id', 'in', self.ids),
            ('move_type', '=', 'in_invoice'),
            ('select_type_inv', '=', 'labor')]
        )
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids.ids)],
        }

    def _add_supplier_to_product(self):
        if not self.partner_id.is_passersby:
            return super(PurchaseOrder, self)._add_supplier_to_product()

    def action_view_invoice_expense_new(self):
        move_ids = self.env['account.move'].search([
            ('purchase_order_product_id', 'in', self.ids),
            ('move_type', '=', 'in_invoice'),
            ('select_type_inv', '=', 'expense')]
        )
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids.ids)],
        }

    def action_view_invoice_service_new(self):
        move_ids = self.env['account.move'].search([
            ('purchase_order_product_id', 'in', self.ids),
            ('move_type', '=', 'in_invoice'),
            ('select_type_inv', '=', 'service')]
        )
        return {
            'name': 'Hóa đơn nhà cung cấp',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids.ids)],
        }

    def create_invoice_normal_yes_return(self, order, line, wave_item):
        data_line = {
            # 'ware_id': wave_item.id,
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
            'discount_value': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax * (wave_item.qty_done / line.product_qty),
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

    def _prepare_invoice_normal(self, line, stock_move_id):
        data_line = {
            'stock_move_id': stock_move_id.id,
            'ware_name': stock_move_id.picking_id.name,
            'po_id': line.id,
            'product_id': line.product_id.id,
            'price_subtotal': line.price_subtotal,
            'promotions': line.free_good,
            'exchange_quantity': line.exchange_quantity,
            'purchase_uom': line.purchase_uom.id,
            'quantity': stock_move_id.quantity_done,
            'vendor_price': line.vendor_price,
            'warehouse': line.location_id.id,
            'discount': line.discount_percent,
            'request_code': line.request_purchases,
            'quantity_purchased': line.purchase_quantity,
            'discount_value': line.discount,
            'tax_ids': line.taxes_id.ids,
            'tax_amount': line.price_tax * (stock_move_id.quantity_done / line.product_qty) if line.product_qty > 0 else 0,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'total_vnd_amount': line.price_subtotal * self.exchange_rate,
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
            # 'ware_id': wave_item.id,
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

    def _prepare_invoice_expense(self, cost_line, po_line, cp):
        # if cost_line.actual_cost <= 0:
        #     return {}
        # amount_rate = po_line.total_vnd_amount / sum(self.order_line.mapped('total_vnd_amount'))
        # cp += ((amount_rate * cost_line.vnd_amount) / po_line.product_qty) * po_line.qty_received
        # if po_line.currency_id != po_line.company_currency:
        #     rates = po_line.currency_id._get_rates(po_line.company_id, self.date_order)
        #     cp = cp * rates.get(po_line.currency_id.id)

        data_line = {
            'po_id': po_line.id,
            'product_id': po_line.product_id.id,
            'product_expense_origin_id': cost_line.product_id.id,
            'description': po_line.product_id.name,
            'account_id': cost_line.product_id.categ_id.property_stock_account_input_categ_id.id,
            'name': cost_line.product_id.name,
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
            # 'ware_id': wave_item.id,
            # 'ware_name': wave_item.picking_id.name,
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
            # 'ware_id': wave_item.id,
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
            'discount_value': line.discount,
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
            'discount_value': line.discount,
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

    def create_invoice_normal_control_len(self, order, line, matching_item, quantity):
        data_line = {
            # 'ware_id': matching_item.id,
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
            'discount_value': line.discount,
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

    def _prepare_invoice_labor(self, labor_cost_id):
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
                                data_line = self._prepare_invoice_labor(labor_cost_id)
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
                                amount_rate = line.total_vnd_amount / sum(self.order_line.mapped('total_vnd_amount'))
                                cp = ((amount_rate * cost_line.vnd_amount) / line.product_qty) * line.qty_received
                                if line.currency_id != line.company_currency:
                                    rates = line.currency_id._get_rates(line.company_id, self.date_order)
                                    cp = cp * rates.get(line.currency_id.id)

                                data_line = self._prepare_invoice_expense(cost_line, line, cp)
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

                if order.select_type_inv == 'normal':
                    if self.purchase_type not in ('service', 'asset'):
                        order._create_invoice_normal_purchase_type_product(invoice_vals_list, invoice_vals)
                    else:
                        invoice_relationship = self.env['account.move'].search([('reference', '=', order.name), ('partner_id', '=', order.partner_id.id), ('purchase_type', '=', order.purchase_type)])
                        if invoice_relationship:
                            if sum(invoice_relationship.invoice_line_ids.mapped('price_subtotal')) == sum(order.order_line.mapped('price_subtotal')):
                                raise UserError(_('Hóa đơn đã được khống chế theo đơn mua hàng!'))
                            else:
                                for line in order.order_line:
                                    wave = invoice_relationship.invoice_line_ids.filtered(lambda w: w.purchase_line_id.id == line.id and w.product_id.id == line.product_id.id)
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
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
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
                    'trade_discount': self.trade_discount if self.total_trade_discounted == 0 else 0,
                    'total_trade_discount': self.total_trade_discount if self.total_trade_discounted == 0 else 0,
                    'x_tax': self.x_tax if self.total_trade_discounted == 0 else 0,
                    'trade_tax_id': self.trade_tax_id.id if self.total_trade_discounted == 0 else False,
                    'x_amount_tax': self.x_amount_tax if self.total_trade_discounted == 0 else 0,
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

            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
            return moves

    def _create_invoice_normal_purchase_type_product(self, invoice_vals_list, invoice_vals):
        sequence = 10
        picking_ids = self.picking_ids.filtered(lambda x: x.state == 'done' and not x.x_is_check_return)
        return_picking_ids = self.picking_ids.filtered(lambda x: x.state == 'done' and x.x_is_check_return)
        return_po_picking_ids = self.return_purchase_ids.picking_ids.filtered(lambda x: x.state == 'done' and x.x_is_check_return)
        pending_section = None
        for line in self.order_line:
            stock_move_ids = picking_ids.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id and x.state == 'done')
            move_refund_ids = return_picking_ids.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id and x.state == 'done')
            move_po_refund_ids = return_po_picking_ids.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id and x.state == 'done')
            qty_refunded = sum(stock_move_ids.mapped('qty_refunded'))
            qty_to_refund = sum(move_refund_ids.mapped('quantity_done')) + sum(move_po_refund_ids.mapped('quantity_done')) - qty_refunded
            for move_id in stock_move_ids.filtered(lambda x: x.quantity_done - x.qty_invoiced - x.qty_refunded > 0):
                data_line = self._prepare_invoice_normal(line, move_id)
                quantity = move_id.quantity_done - move_id.qty_invoiced - move_id.qty_refunded - qty_to_refund
                move_id.write({
                    'qty_invoiced': quantity,
                    'qty_refunded': qty_to_refund,
                })
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update(data_line)
                    line_vals['quantity'] = quantity
                    line_vals['quantity_purchased'] = quantity/line_vals['exchange_quantity']
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
                    pending_section = None

                line_vals = line._prepare_account_move_line()
                line_vals.update(data_line)
                line_vals['quantity'] = quantity
                line_vals['quantity_purchased'] = quantity / line_vals['exchange_quantity']
                line_vals.update({'sequence': sequence})
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                sequence += 1
        if not invoice_vals.get('invoice_line_ids', False):
            raise UserError(_('Tất cả các phiếu nhập kho đã được lên hóa đơn. Vui lòng kiểm tra lại!'))
        invoice_vals_list.append(invoice_vals)

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
                    invoice_vals.update({
                        'purchase_type': order.purchase_type,
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
                            invoice_vals.update({
                                'purchase_type': order.purchase_type,
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
                        invoice_vals.update({
                            'purchase_type': order.purchase_type,
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
                    invoice_vals.update({
                        'purchase_type': order.purchase_type,
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
                domain = [
                    ('origin', 'in', line.purchase_order_product_id.mapped('name')), ('state', '=', 'done'),
                    ('x_is_check_return', '=', False), ('picking_type_id.code', '=', 'incoming')
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
        # if self.location_id:
        #     location_ids |= self.location_id
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
                'is_pk_purchase': True
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

    @api.constrains('total_vnd_exchange_import', 'total_vnd_amount', 'before_tax', 'order_id.is_inter_company','order_id')
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

    # Update fields từ Po line sang stock_move
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for re in res:
            re.update({
                'free_good': self.free_good,
                'quantity_change': self.exchange_quantity,
                'quantity_purchase_done': self.purchase_quantity,
                'quantity_done': self.product_qty,
                'occasion_code_id': self.occasion_code_id.id or False,
                'work_production': self.production_id.id or False,
                'account_analytic_id': self.account_analytic_id.id or False,
            })
        return res

    @api.onchange('asset_code')
    def onchange_asset_code(self):
        if self.asset_code:
            if not self.get_product_code():
                self.product_id = None
                self.name = None
                return {
                    'domain': {
                        'product_id': [('id', '=', 0)],
                        'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]
                    }
                }
        else:
            return {
                'domain': {
                    'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]
                }
            }

    @api.onchange('product_id')
    def onchange_product_id_comput_assets(self):
        if self.order_id.purchase_type == 'asset':
            account = self.product_id.categ_id.property_account_expense_categ_id
            if account:
                return {
                    'domain': {
                        'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id), ('asset_account', '=', account.id)]
                    }
                }
            return {
                'domain': {
                    'asset_code': [('state', '=', 'using'), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]
                }
            }

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
            qty_received = sum(item._get_po_line_moves().filtered(lambda x: not x.to_refund and x.state == 'done').mapped('quantity_done'))
            qty_returned = item.qty_returned or 0
            item.received = qty_received/item.exchange_quantity - qty_returned if qty_received and item.exchange_quantity else 0

    def compute_billed(self):
        for item in self:
            item.billed = item.qty_invoiced/item.exchange_quantity if item.exchange_quantity else 0

    @api.depends('exchange_quantity', 'product_qty', 'product_id', 'purchase_uom', 'order_id.purchase_type', 'vendor_price_import',
                 'order_id.partner_id', 'order_id.partner_id.is_passersby', 'order_id', 'order_id.currency_id',
                 'free_good')
    def compute_vendor_price_ncc(self):
        today = datetime.now().date()
        for rec in self:
            if rec.free_good:
                rec.vendor_price = 0
                rec.price_subtotal = 0

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
                rec.write({
                    'discount': 0,
                    'discount_percent': 0,
                    'readonly_discount_percent': True,
                    'readonly_discount': True,
                })
            else:
                rec.write({
                    'readonly_discount_percent': False,
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
        location_dest_id = self.location_id.id if self.location_id else (self.order_id.location_id.id if self.order_id.location_id else False)
        if not location_dest_id:
            location_dest_id = (self.orderpoint_id and not (
                self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location()
        if not self.order_id.is_return:
            picking_id = picking.filtered(lambda p: p.location_dest_id and p.location_dest_id.id == location_dest_id)
        else:
            picking_id = picking.filtered(lambda p: p.location_id and p.location_id.id == location_dest_id)

        return {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.product_id.display_name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': location_dest_id,
            'picking_id': picking_id.id,
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

