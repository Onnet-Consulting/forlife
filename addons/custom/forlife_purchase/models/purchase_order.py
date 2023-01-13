from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_type = fields.Selection([
        ('goods', 'Goods'),
        ('service', 'Service'),
        ('asset', 'Asset'),
    ], string='Purchase Type')
    # purchase_description = fields.Char(string='Purchase Description')
    # request_date = fields.Date(string='Request date')
    purchase_code = fields.Char(string='Internal order number')
    has_contract = fields.Boolean(string='Contract?')
    has_invoice = fields.Boolean(string='Finance Bill?')

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Exchange')
    manual_currency_exchange_rate = fields.Float('Rate', digits=(12, 6))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', compute='_compute_active_manual_currency_rate')

    prod_filter = fields.Boolean(string='Filter Products by Supplier', default=True)
    total_discount = fields.Monetary(string='Total Discount', store=True, readonly=True,
                                     compute='_amount_all', tracking=True)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Download Template for Purchase Order'),
            'template': '/forlife_purchase/static/src/xlsx/TemplatePO.xlsx?download=true'
        }]

    @api.depends('order_line.price_total', 'order_line.discount')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = total_discount = 0.0
            for line in order.order_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                total_discount += line.discount

            IrConfigPrmtrSudo = self.env['ir.config_parameter'].sudo()
            discTax = IrConfigPrmtrSudo.get_param('account.global_discount_tax')

            if discTax == 'taxed':
                total = amount_untaxed + amount_tax
            else:
                total = amount_untaxed

            if discTax != 'taxed':
                total += amount_tax

            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': total,
                'total_discount': total_discount,
            })

    # exchange rate

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

    def _prepare_invoice(self):
        result = super(PurchaseOrder, self)._prepare_invoice()
        result.update({
            'apply_manual_currency_exchange': self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate': self.manual_currency_exchange_rate,
            'active_manual_currency_rate': self.active_manual_currency_rate
        })
        return result

    def _prepare_picking(self):
        result = super(PurchaseOrder, self)._prepare_picking()
        diff_currency = False
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                diff_currency = True
            else:
                diff_currency = False
        else:
            diff_currency = False
        if diff_currency:
            result.update({
                'apply_manual_currency_exchange': self.apply_manual_currency_exchange,
                'manual_currency_exchange_rate': self.manual_currency_exchange_rate,
                'active_manual_currency_rate': diff_currency
            })
        return result

    @api.onchange('company_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends('price_unit', 'discount', 'taxes_id', 'product_qty')
    def _get_line_subtotal(self):
        for line in self:
            if line.free_good:
                line.line_sub_total = 0.0
            else:
                price = line.price_unit
                quantity = line.product_qty
                taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, quantity,
                                                  product=line.product_id, partner=line.order_id.partner_id)
                line.line_sub_total = taxes['total_excluded']

    asset_code = fields.Char(string='Asset code')
    secondary_quantity = fields.Float('Quantity of Exchange', digits='Product Unit of Measure')
    line_sub_total = fields.Monetary(compute='_get_line_subtotal', string='Line Subtotal', readonly=True, store=True)
    discount_percent = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    discount = fields.Float(string='Discount (Amount)', digits='Discount', default=0.0)
    free_good = fields.Boolean(string='Free Goods')
    warehouses_id = fields.Many2one('stock.warehouse', string="Whs")
    production_id = fields.Many2one('forlife.production', string='Production Order Code')
    cost_center_id = fields.Many2one('cost.center', string='Cost Center')
    request_line_id = fields.Many2one('purchase.request', string='Purchase Request')
    event_id = fields.Many2one('forlife.event', string='Program of events')

    _sql_constraints = [
        (
            "discount_limit",
            "CHECK (discount_percent <= 100.0)",
            "Discount Pervent must be lower than 100%.",
        )
    ]

    #discount

    def _convert_to_tax_base_line_dict(self):
        if self.discount:
            price = self.price_unit * self.product_qty - (self.discount or 0.0)
        else:
            price = self.price_unit * (1 - (self.discount_percent or 0.0) / 100.0)
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=price,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )

    #exchange rate
    # @api.onchange('product_qty', 'product_uom')
    # def _onchange_quantity(self):
    #     if not self.product_id:
    #         return
    #     params = {'order_id': self.order_id}
    #     seller = self.product_id._select_seller(
    #         partner_id=self.partner_id,
    #         quantity=self.product_qty,
    #         date=self.order_id.date_order and self.order_id.date_order.date(),
    #         uom_id=self.product_uom,
    #         params=params)
    #
    #     if seller or not self.date_planned:
    #         self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #
    #     # If not seller, use the standard price. It needs a proper currency conversion.
    #     if not seller:
    #         price_unit = self.env['account.tax']._fix_tax_included_price_company(
    #             self.product_id.uom_id._compute_price(self.product_id.standard_price, self.product_id.uom_po_id),
    #             self.product_id.supplier_taxes_id,
    #             self.taxes_id,
    #             self.company_id,
    #         )
    #         if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
    #             price_unit = self.order_id.company_id.currency_id._convert(
    #                 price_unit,
    #                 self.order_id.currency_id,
    #                 self.order_id.company_id,
    #                 self.date_order or fields.Date.today(),
    #             )
    #         self.price_unit = price_unit
    #         return
    #
    #     price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
    #                                                                          self.product_id.supplier_taxes_id,
    #                                                                          self.taxes_id,
    #                                                                          self.company_id) if seller else 0.0
    #     if self.order_id.apply_manual_currency_exchange:
    #         self.price_unit = price_unit * self.order_id.manual_currency_exchange_rate
    #         return
    #     if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
    #         price_unit = seller.currency_id._convert(
    #             price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())
    #
    #     if seller and self.product_uom and seller.product_uom != self.product_uom:
    #         price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)
    #
    #     self.price_unit = price_unit

    def _get_stock_move_price_unit(self):
        self.ensure_one()
        line = self[0]
        order = line.order_id
        price_unit = line.price_unit
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        if line.taxes_id:
            qty = line.product_qty or 1
            price_unit = line.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=line.order_id.currency_id, quantity=qty, product=line.product_id,
                partner=line.order_id.partner_id
            )['total_void']
            price_unit = round(price_unit / qty, int(price_unit_prec))
        if line.product_uom and line.product_id and line.product_id.uom_id:
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            if order.active_manual_currency_rate and order.apply_manual_currency_exchange:
                price_unit = price_unit / (1 / order.manual_currency_exchange_rate)
            else:
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(),
                    round=False)
        return price_unit
