from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import json


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
    ], string='Inventory Status', default='not_received', required=True)
    # purchase_description = fields.Char(string='Purchase Description')
    # request_date = fields.Date(string='Request date')
    purchase_code = fields.Char(string='Internal order number')
    has_contract = fields.Boolean(string='Contract?')
    has_invoice = fields.Boolean(string='Finance Bill?')
    exchange_rate = fields.Float(string='Exchange Rate', default=1)


    # apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange', compute='_compute_active_manual_currency_rate')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', compute='_compute_active_manual_currency_rate')
    production_id = fields.Many2one('forlife.production', string='Production Order Code')

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
    exchange_rate_line = fields.One2many('purchase.order.exchange.rate', 'purchase_order_id')
    cost_line = fields.One2many('purchase.order.cost.line', 'purchase_order_id')
    is_passersby = fields.Boolean(related='partner_id.is_passersby')
    location_id = fields.Many2one('stock.location', string="Địa điểm kho", check_company=True)
    is_inter_company = fields.Boolean(default=False)
    partner_domain = fields.Char(compute='compute_partner_domain')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES, change_default=True, tracking=True, domain=False, help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    occasion_code_ids = fields.Many2many('occasion.code', relation='occasion_code_ref', string="Case Code")
    account_analytic_ids = fields.Many2many('account.analytic.account', relation='account_analytic_ref', string="Cost Center")
    is_purchase_request = fields.Boolean(default=False)
    source_document = fields.Char(string="Source Document")
    receive_date = fields.Datetime(string='Receive Date')
    note = fields.Char('Note')

    @api.depends('is_inter_company')
    def compute_partner_domain(self):
        for item in self:
            data_search = self.env['res.partner'].search([('is_inter_company_purchase', '=', True if item.is_inter_company else False), ('company_id', '=', False)])
            item.partner_domain = json.dumps([('id', 'in', data_search.ids)])

    def action_confirm(self):
        for record in self:
            record.write({'custom_state': 'confirm'})

    def action_approved(self):
        super(PurchaseOrder, self).button_confirm()
        for record in self:
            record.write({'custom_state': 'approved'})


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
        return [{
            'label': _('Download Template for Purchase Order'),
            'template': '/forlife_purchase/static/src/xlsx/TemplatePO.xlsx?download=true'
        }]

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
        self.cost_line = [(5, 0)]
        for line in self.order_line:
            self.env['purchase.order.exchange.rate'].create({
                'product_id': line.product_id.id,
                'name': line.name,
                'usd_amount': line.price_subtotal,
                'purchase_order_id': self.id
            })
            self.env['purchase.order.cost.line'].create({
                'product_id': line.product_id.id,
                'name': line.name,
                'usd_amount': line.price_subtotal,
                'purchase_order_id': self.id
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
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                # Current value always = 0
                # if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
                    pending_section = None
                line_vals = line._prepare_account_move_line()
                line_vals.update({'sequence': sequence})
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

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
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'is_check': True,
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
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        return self.action_view_invoice(moves)


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
    asset_code = fields.Char(string='Asset code')
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
    request_line_id = fields.Many2one('purchase.request', string='Purchase Request')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    vendor_price = fields.Float(string='Vendor Price')
    readonly_discount = fields.Boolean(default=False)
    readonly_discount_percent = fields.Boolean(default=False)
    billed = fields.Float(string='Billed')
    request_purchases = fields.Char(string='Purchases', readonly=1)
    is_passersby = fields.Boolean(related='order_id.is_passersby')
    supplier_id = fields.Many2one('res.partner', related='order_id.partner_id')
    receive_date = fields.Datetime(string='Date receive')
    tolerance = fields.Float(related='product_id.tolerance')
    received = fields.Integer(string='Received')

    _sql_constraints = [
        (
            "discount_limit",
            "CHECK (discount_percent <= 100.0)",
            "Discount Pervent must be lower than 100%.",
        )
    ]

    @api.onchange('product_id', 'supplier_id', 'is_passersby')
    def onchange_vendor_price(self):
        if not self.is_passersby:
            if self.product_id and self.supplier_id:
                data = self.env['product.supplierinfo'].search([('partner_id', '=', self.supplier_id.id), (
                'product_tmpl_id' , '=', self.product_id.product_tmpl_id.id)])
                if data:
                    self.vendor_price = data.price

    @api.onchange('product_id', 'order_id')
    def onchange_receive_date(self):
        if self.order_id:
            self.receive_date = self.order_id.receive_date

    #discount

    @api.onchange("free_good")
    def _onchange_free_good(self):
        if self.free_good:
            self.discount = self.discount_percent = False
            self.readonly_discount_percent = self.readonly_discount = True
        else:
            self.readonly_discount_percent = self.readonly_discount = False

    @api.onchange("vendor_price")
    def _onchange_vendor_price(self):
        self.price_unit = self.vendor_price/self.exchange_quantity if self.exchange_quantity else False

    @api.onchange("discount_percent")
    def _onchange_discount_percent(self):
        if not self.readonly_discount_percent:
            if self.discount_percent:
                self.discount = self.discount_percent*self.price_unit*0.01
                self.readonly_discount = True
            else:
                self.readonly_discount = False

    @api.onchange("discount")
    def _onchange_discount(self):
        if not self.readonly_discount:
            if self.discount:
                self.discount_percent = (self.discount/self.price_unit)*100 if self.price_unit else 0
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

    #exchange rate
    @api.depends('purchase_quantity', 'purchase_uom', 'product_qty', 'product_uom')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines:
                continue
            params = {'order_id': line.order_id}
            uom_id = line.purchase_uom if  line.product_id.detailed_type == 'product' else line.product_uom
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

            if line.product_id.detailed_type == 'product':
                line.vendor_price = seller.product_uom._compute_price(price_unit, line.product_uom)
                line.price_unit = line.vendor_price/line.exchange_quantity if line.exchange_quantity else 0.0
            else:
                line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)

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
        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.partner_id == self.order_id.partner_id and (not r.product_id or r.product_id == self.product_id))\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
        else:
            self.product_qty = 1.0
        # re-write thông tin purchase_uom,product_uom
        self.product_uom = self.product_id.uom_id
        self.purchase_uom = self.product_id.uom_id

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
        location_dest_id = self.location_id.id if self.location_id else (self.order_id.location_id.id if self.order_id.location_id else False)
        if not location_dest_id:
            location_dest_id = (self.orderpoint_id and not (self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location()
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

