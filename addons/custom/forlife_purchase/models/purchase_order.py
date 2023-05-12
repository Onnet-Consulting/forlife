import datetime

from odoo import api, fields, models, _
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
        ('asset', 'Asset'),
    ], string='Purchase Type', required=True, default='product')
    inventory_status = fields.Selection([
        ('not_received', 'Not Received'),
        ('incomplete', 'Incomplete'),
        ('done', 'Done'),
    ], string='Inventory Status', default='not_received', compute='compute_inventory_status')
    # purchase_description = fields.Char(string='Purchase Description')
    # request_date = fields.Date(string='Request date')
    purchase_code = fields.Char(string='Internal order number')
    has_contract = fields.Boolean(string='Hợp đồng khung?')
    has_invoice = fields.Boolean(string='Finance Bill?')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 8), default=1)

    # apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange', compute='_compute_active_manual_currency_rate')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency',
                                                 compute='_compute_active_manual_currency_rate')
    production_id = fields.Many2one('forlife.production', string='Production Order Code', ondelete='restrict')

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
                                         string="Thuế nhập khẩu")
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
    rejection_reason = fields.Char(string="Lý do từ chối")
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)", compute='compute_origin')
    type_po_cost = fields.Selection([('tax', 'Tax'), ('cost', 'Cost')])

    # Lấy của base về phục vụ import
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Chi tiết',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    payment_term_id = fields.Many2one('account.payment.term', 'Chính sách thanh toán',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.constrains('cost_line')
    def constrains_product_line(self):
        for rec in self:
            if not rec.cost_line.product_id:
                raise ValidationError('Cần điền đầy đủ phần chi phí')

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

    @api.depends('cost_line', 'cost_line.expensive_total')
    def compute_cost_total(self):
        for item in self:
            item.cost_total = sum(item.cost_line.mapped('expensive_total'))

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

    ## Các action header
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
                    'domain': [('id', '=', ncc.ids)],
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
                'domain': [('id', '=', customer.ids)],
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

    ## Compute field action hearder
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
                item.count_invoice_inter_company_ncc = len(
                    self.data_account_move([('reference', '=', so.name), ('is_from_ncc', '=', True)]))
            else:
                item.count_invoice_inter_company_ncc = False

    @api.onchange('trade_discount')
    def onchange_total_trade_discount(self):
        if self.trade_discount:
            if self.tax_totals.get('amount_total') and self.tax_totals.get('amount_total') != 0:
                self.total_trade_discount = self.tax_totals.get('amount_total') / self.trade_discount

    def action_confirm(self):
        for record in self:
            record.write({'custom_state': 'confirm'})

    def action_approved(self):
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
                if picking_in:
                    for orl in record.order_line:
                        for pkl in picking_in.move_ids_without_package:
                            if orl.product_id == pkl.product_id and orl.location_id.id == pkl.location_dest_id.id:
                                pkl.write({
                                    'quantity_done': orl.product_qty,
                                    'occasion_code_id': orl.occasion_code_id.id,
                                    'work_production': orl.production_id.id,
                                })

                        for pk in picking_in.move_line_ids_without_package:
                            if orl.product_id == pk.product_id and orl.location_id.id == pk.location_dest_id.id:
                                pk.write({
                                    'purchase_uom': orl.purchase_uom,
                                    'quantity_change': orl.exchange_quantity,
                                })
                record.write({'custom_state': 'approved'})
            else:
                data = {'partner_id': record.partner_id.id, 'purchase_type': record.purchase_type,
                        'is_purchase_request': record.is_purchase_request, 'production_id': record.production_id.id,
                        'event_id': record.event_id, 'currency_id': record.currency_id.id,
                        'exchange_rate': record.exchange_rate,
                        'manual_currency_exchange_rate': record.manual_currency_exchange_rate,
                        'company_id': record.company_id.id, 'has_contract': record.has_contract,
                        'has_invoice': record.has_invoice,
                        'location_id': record.location_id.id, 'source_location_id': record.source_location_id.id,
                        'date_order': record.date_order,
                        'payment_term_id': record.payment_term_id.id,
                        'date_planned': record.date_planned, 'receive_date': record.receive_date,
                        'inventory_status': record.inventory_status, 'picking_type_id': record.picking_type_id.id,
                        'source_document': record.source_document,
                        'has_contract_commerce': record.has_contract_commerce, 'note': record.note,
                        'receipt_reminder_email': record.receipt_reminder_email,
                        'reminder_date_before_receipt': record.reminder_date_before_receipt,
                        'dest_address_id': record.dest_address_id.id, 'purchase_order_id': record.id,
                        'name': record.name,
                        }
                order_line = []
                invoice_line_ids = []
                uom = self.env.ref('uom.product_uom_unit').id
                for line in record.order_line:
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
                        'discount_invoice': line.discount,
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
            record.write({'custom_state': 'approved', 'inventory_status': 'done', 'invoice_status': 'invoiced'})

    def supplier_sales_order(self, data, order_line, invoice_line_ids):
        company_partner = self.env['res.partner'].search([('internal_code', '=', '3001')], limit=1)
        partner_so = self.env['res.partner'].search([('internal_code', '=', '3000')], limit=1)
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
                    'picking_type_id': self.env.ref('stock.picking_type_in').id,
                    'partner_id': company_partner.id,
                    'location_id': self.env.ref('forlife_stock.export_production_order').id,
                    'location_dest_id': data.get('location_id'),
                    'scheduled_date': datetime.datetime.now(),
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
            ## Sử lý hóa đơn
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
            ## Vào sổ hóa đơn bán hàng
            invoice_ncc.action_post()
            invoice_customer.write({
                'invoice_date': datetime.datetime.now(),
                'move_type': 'in_invoice',
                'reference': data.get('name'),
                'is_from_ncc': False
            })
            sql = f"""update account_move set partner_id = {data.get('partner_id')} where id = {invoice_customer.id}"""
            self._cr.execute(sql)
            ##Vào sổ hóa đơn mua hàng
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

    # def _prepare_invoice(self):
    #     result = super(PurchaseOrder, self)._prepare_invoice()
    #     result.update({
    #         'manual_currency_exchange_rate': self.manual_currency_exchange_rate,
    #         'active_manual_currency_rate': self.active_manual_currency_rate
    #     })
    #     return result

    # def _prepare_picking(self):
    #     result = super(PurchaseOrder, self)._prepare_picking()
    #     diff_currency = False
    #     if self.company_id or self.currency_id:
    #         if self.company_id.currency_id != self.currency_id:
    #             diff_currency = True
    #         else:
    #             diff_currency = False
    #     else:
    #         diff_currency = False
    #     if diff_currency:
    #         result.update({
    #             'apply_manual_currency_exchange': self.apply_manual_currency_exchange,
    #             'manual_currency_exchange_rate': self.manual_currency_exchange_rate,
    #             'active_manual_currency_rate': diff_currency
    #         })
    #     return result

    @api.onchange('company_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.onchange('order_line')
    def onchange_order_line(self):
        self.exchange_rate_line = [(5, 0)]
        for line in self.order_line:
            self.env['purchase.order.exchange.rate'].create({
                'product_id': line.product_id.id,
                'name': line.name,
                'usd_amount': line.price_subtotal,
                'purchase_order_id': self.id,
                'qty_product': line.product_qty
            })

    def action_update_import(self):
        for item in self:
            item.exchange_rate_line = [(5, 0)]
            for line in item.order_line:
                self.env['purchase.order.exchange.rate'].create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'usd_amount': line.price_subtotal,
                    'purchase_order_id': item.id,
                    'qty_product': line.product_qty
                })

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

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        if len(self) > 1 and self[0].type_po_cost in ('cost', 'tax'):
            result = self.create_multi_invoice_vendor()
        else:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            sequence = 10
            for order in self:
                if order.custom_state != 'approved':
                    raise UserError(
                        _('Tạo hóa đơn không hợp lệ!'))
                # Disable because custom state
                # if order.invoice_status != 'to invoice':
                #     continue
                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                invoice_vals.update({'purchase_type': order.purchase_type, 'invoice_date': datetime.datetime.now(),
                                     'exchange_rate': order.exchange_rate, 'currency_id': order.currency_id.id})
                # Invoice line values (keep only necessary sections).
                for line in order.order_line:
                    data_line = {'sequence': sequence, 'price_subtotal': line.price_subtotal,
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
                                 'discount_invoice': line.discount,
                                 'taxes_id': line.taxes_id.id,
                                 'tax_amount': line.price_tax,
                                 'uom_id': line.product_uom.id,
                                 'price_unit': line.price_unit}
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                    # Current value always = 0
                    # if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
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

            if not invoice_vals_list:
                raise UserError(
                    _('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

            # 2) group by (company_id, partner_id, currency_id) for batch creation
            new_invoice_vals_list = []
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                    x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                # request_co = []
                # request_co.append((0, 0, {
                #     'request_code': self.source_document
                # }))
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'purchase_type': self.purchase_type if len(self) == 1 else 'product',
                    'reference': ', '.join(self.mapped('name')),
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'is_check': True,
                    # 'invoice_line_ids': request_co,
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)
            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(
                lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
            return self.action_view_invoice(moves)

    def create_multi_invoice_vendor(self):
        sequence = 10
        vals_all_invoice = {}
        for order in self:
            if order.inventory_status != 'done' and order.purchase_type == 'product':
                raise ValidationError(
                    'Phiếu nhận hàng của đơn mua hàng %s có thể chưa hoàn thành/chưa có!' % (order.name))
            if order.custom_state != 'approved':
                raise UserError(
                    _('Tạo hóa đơn không hợp lệ!'))
            for line in order.order_line:
                data_line = {'sequence': sequence, 'price_subtotal': line.price_subtotal,
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
                             'discount_invoice': line.discount,
                             'taxes_id': line.taxes_id.id,
                             'tax_amount': line.price_tax,
                             'uom_id': line.product_uom.id,
                             'price_unit': line.price_unit}
                sequence += 1
                key = order.purchase_type
                invoice_vals = order._prepare_invoice()
                invoice_vals.update({'purchase_type': order.purchase_type, 'invoice_date': datetime.datetime.now(),
                                     'exchange_rate': order.exchange_rate, 'currency_id': order.currency_id})
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
        moves = self.env['account.move']
        for data in vals_all_invoice:
            move = moves.create(vals_all_invoice.get(data)).action_post()
        return True

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
    vendor_price = fields.Float(string='Vendor Price')
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
    is_red_color = fields.Boolean(compute='compute_is_red_color')
    name = fields.Char(default="Tên sản phẩm", required=False)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', store=True, required=False)

    @api.model
    def create(self, vals):
        line = super(PurchaseOrderLine, self).create(vals)
        if not line.product_uom or not line.name:
            line.product_uom = line.product_id.uom_id.id
            line.name = line.product_id.name
        return line

    @api.depends('exchange_quantity')
    def compute_is_red_color(self):
        date_item = datetime.datetime.now().date()
        for item in self:
            if not (item.product_id and item.supplier_id and item.purchase_uom):
                item.is_red_color = False
                continue
            supplier_info = self.search_product_sup(
                [('product_uom', '=', item.purchase_uom.id),
                 ('product_id', '=', item.product_id.id),
                 ('partner_id', '=', item.supplier_id.id),
                 ('date_start', '<', date_item),
                 ('date_end', '>', date_item)])
            item.is_red_color = True if item.exchange_quantity not in supplier_info.mapped(
                'amount_conversion') else False

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            date_item = datetime.datetime.now().date()
            supplier_info = self.search_product_sup(
                [('product_id', '=', self.product_id.id), ('partner_id', '=', self.supplier_id.id),
                 ('date_start', '<', date_item),
                 ('date_end', '>', date_item)])
            if supplier_info:
                self.purchase_uom = supplier_info[-1].product_uom

    @api.depends('supplier_id', 'product_id', )
    def compute_domain_uom(self):
        for item in self:
            date_item = datetime.datetime.now().date()
            supplier_info = self.search_product_sup(
                [('product_id', '=', item.product_id.id), ('partner_id', '=', item.supplier_id.id),
                 ('date_start', '<', date_item),
                 ('date_end', '>', date_item)]) if item.supplier_id and item.product_id else None
            item.domain_uom = json.dumps(
                [('id', 'in', supplier_info.mapped('product_uom').ids)]) if supplier_info else json.dumps([])

    def search_product_sup(self, domain):
        supplier_info = self.env['product.supplierinfo'].search(domain)
        return supplier_info

    @api.constrains('asset_code')
    def constrains_asset_code(self):
        for item in self:
            if item.order_id.purchase_type == 'asset':
                if item.asset_code and item.asset_code.asset_account.code and item.product_id and item.product_id.categ_id and item.product_id.categ_id.property_valuation == 'real_time' and item.product_id.categ_id.property_stock_valuation_account_id:
                    if item.asset_code.asset_account.code != item.product_id.categ_id.property_stock_valuation_account_id.code:
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

    @api.onchange('exchange_quantity', 'product_id', 'supplier_id', 'purchase_uom')
    def onchange_unit_price(self):
        if all((self.product_id, self.supplier_id, self.purchase_uom, not self.is_red_color)):
            data = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                ('partner_id', '=', self.supplier_id.id),
                ('product_uom', '=', self.purchase_uom.id),
                ('amount_conversion', '=', self.exchange_quantity)
            ], limit=1)
            self.vendor_price = data.price if data else False
        else:
            self.vendor_price = False

    @api.onchange('product_id', 'supplier_id', 'is_passersby', )
    def onchange_vendor_price(self):
        if not self.is_passersby:
            if self.product_id and self.supplier_id and self.purchase_uom:
                data = self.env['product.supplierinfo'].search(
                    [('product_uom', '=', self.purchase_uom.id), ('partner_id', '=', self.supplier_id.id), (
                        'product_tmpl_id', '=', self.product_id.product_tmpl_id.id)], limit=1)
                if data:
                    self.exchange_quantity = data.amount_conversion

    @api.onchange('free_good')
    def onchange_vendor_prices(self):
        if self.free_good:
            self.vendor_price = False

    @api.onchange('vendor_price', 'exchange_quantity')
    def onchange_price_unit(self):
            self.price_unit = self.vendor_price / self.exchange_quantity if self.exchange_quantity else False

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
            if self.discount:
                self.discount_percent = (self.discount / self.price_unit) * 100 if self.price_unit else 0
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
                raise ValidationError(_('Purchase quantity cannot be negative !!'))

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
                invoice_line = []
                invoice_line_cost_in_tax = []
                if po.type_po_cost == 'tax':
                    if po.exchange_rate_line:
                        invoice_line = self.create_invoice_po_tax(po, record)
                    if po.cost_line:
                        invoice_line_cost_in_tax = self.create_invoice_po_cost(po, record)
                        account_cost_in_tax = self.create_account_move(po, invoice_line_cost_in_tax, record)
                elif po.type_po_cost == 'cost':
                    invoice_line = self.create_invoice_po_cost(po, record)
                if po.type_po_cost in ('cost', 'tax'):
                    if invoice_line:
                        account = self.create_account_move(po, invoice_line, record)
                ##Tạo nhập khác xuất khác khi nhập kho
                if po.order_line_production_order and not po.is_inter_company:
                    npl = self.create_invoice_npl(po, record)
        return res

    def create_account_move(self, po, line, record):
        master_data_ac = {
            'ref': record.name,
            'purchase_type': po.purchase_type,
            'move_type': 'entry',
            'reference': po.name,
            'currency_id': po.currency_id.id,
            'exchange_rate': po.exchange_rate,
            'date': datetime.datetime.now(),
            'invoice_payment_term_id': po.payment_term_id.id,
            'invoice_date_due': po.date_planned,
            'invoice_line_ids': line,
            'restrict_mode_hash_table': False
        }
        account_obj = self.env['account.move']
        account = account_obj.create(master_data_ac)
        account.action_post()
        return True

    # Xử lý bút toán po nội bộ
    def create_invoice_po_cost(self, po, record):
        data_in_line = po.order_line
        invoice_line_cost_in_tax = []
        vals = {}
        list_money = []
        for po_l, pk_l in zip(po.order_line, record.move_ids_without_package):
            list_money.append(pk_l.quantity_done * po_l.price_unit - po_l.discount)
        total_money = sum(list_money)
        if total_money <= 0:
            raise ValidationError('Tổng tiền của sản phẩm là 0')
        for item, total, range_product in zip(data_in_line, list_money, range(1, len(data_in_line) + 1)):
            if item.product_id.categ_id and item.product_id.categ_id.property_stock_valuation_account_id:
                account_1561 = item.product_id.categ_id.property_stock_valuation_account_id.id
            else:
                raise ValidationError('Danh mục của sản phẩm chưa được cấu hình!')
            for rec in po.cost_line:

                if rec.product_id.categ_id and rec.product_id.categ_id.property_stock_valuation_account_id:
                    account_acc = rec.product_id.categ_id.property_stock_account_input_categ_id.id
                else:
                    raise ValidationError('Danh mục của sản phẩm chưa được cấu hình!')
                key_acc = str(account_acc) + "_" + rec.name
                if not vals.get(key_acc):
                    vals.update({
                        key_acc: {'account_id': account_acc,
                                  'name': rec.name,
                                  'debit': 0,
                                  'credit': total / total_money * rec.expensive_total,
                                  },
                    })
                    for pro, len_pro in zip(data_in_line, range(1, len(data_in_line) + 1)):
                        vals.update({
                            "1561" + "from" + str(len_pro) + str(pro.product_id) + key_acc: {
                                'account_id': account_1561, 'name': "Auto",
                                'debit': 0,
                                'credit': 0,
                            }
                        })
                    vals["1561" + "from" + str(range_product) + str(item.product_id) + key_acc].update({
                        'account_id': account_1561, 'name': item.name,
                        'debit': total / total_money * rec.expensive_total,
                        'credit': 0,
                    })
                else:
                    vals[key_acc]["credit"] = vals[key_acc]["credit"] + (
                            total / total_money * rec.expensive_total)
                    vals["1561" + "from" + str(range_product) + str(item.product_id) + key_acc].update({
                        'account_id': account_1561, 'name': item.name,
                        'debit': total / total_money * rec.expensive_total,
                        'credit': 0,
                    })
        for line in vals:
            invoice_line_cost_in_tax.append((0, 0, vals.get(line)))
        return invoice_line_cost_in_tax

    # Xử lý bút toán po nhập khẩu
    def create_invoice_po_tax(self, po, record):
        invoice_line = []
        for r, stock in zip(po.exchange_rate_line, record.move_ids_without_package):
            if r.product_id.categ_id and r.product_id.categ_id.property_stock_valuation_account_id:
                account_1561 = r.product_id.categ_id.property_stock_valuation_account_id.id
            else:
                raise ValidationError('Danh mục của sản phẩm chưa được cấu hình!')
            if r.qty_product <= 0 or stock.quantity_done <= 0:
                raise ValidationError('Số lượng sản phẩm nhập hay số lương hoàn thành phải lớn hơn 0')
            credit_333 = stock.quantity_done / r.qty_product * r.tax_amount
            credit_332 = stock.quantity_done / r.qty_product * r.special_consumption_tax_amount
            invoice_line_1561 = (
                0, 0,
                {
                    'account_id': account_1561, 'name': r.name,
                    'debit': credit_333 + credit_332,
                    'credit': 0,
                })
            invoice_line_3333 = (
                0, 0,
                {'account_id': self.env.ref(
                    'forlife_purchase.product_import_tax').categ_id.property_stock_account_input_categ_id.id,
                 'name': r.name,
                 'debit': 0,
                 'credit': credit_333,
                 })
            invoice_line_3332 = (
                0, 0,
                {'account_id': self.env.ref(
                    'forlife_purchase.product_excise_tax').categ_id.property_stock_account_input_categ_id.id,
                 'name': r.name,
                 'debit': 0,
                 'credit': credit_332,
                 })
            lines = [invoice_line_1561, invoice_line_3333, invoice_line_3332]
            invoice_line.extend(lines)
        return invoice_line

    # Xử lý bút toán po nguyên phụ liệu
    def create_invoice_npl(self, po, record):
        list_line_xk = []
        invoice_line_npls = []
        for item in po.order_line_production_order:
            material = self.env['purchase.order.line.material.line'].search(
                [('purchase_order_line_id', '=', item.id)])
            if not material:
                raise ValidationError('Bạn chưa cấu hình nguyên phụ liệu trong đơn mua hàng')
            if item.product_id.categ_id and item.product_id.categ_id.property_stock_valuation_account_id:
                account_1561 = item.product_id.categ_id.property_stock_valuation_account_id.id
            else:
                raise ValidationError("Danh mục sản phẩm chưa được cấu hình đúng")
            debit = 0
            for material_line in material:
                number_product = self.env['stock.quant'].search(
                    [('location_id', '=', record.location_dest_id.id),
                     ('product_id', '=', material_line.product_id.id)])
                # if not number_product or sum(number_product.mapped('quantity')) < material_line.product_plan_qty:
                #     raise ValidationError('Số lượng sản phẩm trong kho không đủ')
                if not self.env.ref('forlife_stock.export_production_order').valuation_in_account_id:
                    raise ValidationError('Tài khoản định giá tồn kho trong lý do xuất nguyên phụ liệu không tồn tại')
                list_line_xk.append((0, 0, {
                    'product_id': material_line.product_id.id,
                    'product_uom': material_line.uom.id,
                    'price_unit': material_line.price_unit,
                    'location_id': record.location_dest_id.id,
                    'location_dest_id': self.env.ref('forlife_stock.export_production_order').id,
                    'product_uom_qty': material_line.product_plan_qty,
                    'quantity_done': material_line.product_plan_qty,
                    'amount_total': material_line.price_unit * material_line.product_plan_qty,
                    'reason_type_id': self.env.ref('forlife_stock.reason_type_6').id,
                    'reason_id': self.env.ref('forlife_stock.export_production_order').id,
                }))
                # Tạo bút toán cho nguyên phụ liệu
                credit = material_line.price_unit * material_line.product_plan_qty
                credit_npl = (0, 0, {
                    'account_id': self.env.ref(
                        'forlife_stock.export_production_order').valuation_in_account_id.id,
                    'name': material_line.product_id.name,
                    'debit': 0,
                    'credit': credit,
                })
                invoice_line_npls.append(credit_npl)
                debit += credit
                # end
            debit_npl = (0, 0, {
                'account_id': account_1561, 'name': item.product_id.name,
                'debit': debit,
                'credit': 0,
            })
            invoice_line_npls.append(debit_npl)
        account_nl = self.create_account_move(po, invoice_line_npls, record)
        master_xk = self.create_xk_picking(po, record, list_line_xk)
        return master_xk

    def create_xk_picking(self, po, record, list_line_xk):
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'location_id': record.location_dest_id.id,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_6').id,
            'location_dest_id': self.env.ref('forlife_stock.export_production_order').id,
            'scheduled_date': datetime.datetime.now(),
            'origin': po.name,
            'other_export': True,
            'state': 'assigned',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'move_ids_without_package': list_line_xk
        }
        result = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(
            master_xk).button_validate()
        return result
