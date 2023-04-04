from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    # def _domain_purchase_order(self):
    #     return [('custom_state', '=', 'approved')]
    invoice_description = fields.Char(string="Invoce Description")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    purchase_type = fields.Selection([
        ('product', 'Goods'),
        ('service', 'Service'),
        ('asset', 'Asset'),
    ], string='PO Type', default='product')
    number_bills = fields.Char(string='Number bills')
    bill_date = fields.Datetime(string='Bill Date')
    due_date = fields.Datetime(string='Due Date')
    reference = fields.Char(string='Source Material')
    exchange_rate = fields.Float(string="Exchange Rate", default=1)
    accounting_date = fields.Datetime(string='Accounting Date')
    payment_term = fields.Many2one('account.payment.term', string='Payment Policy')
    payment_status = fields.Char(string='Payment status')


    receiving_warehouse_id = fields.Char(string='Receiving Warehouse')
    purchase_order_product_id = fields.Many2one('purchase.order', string='Purchase Order')
    purchase_order_id = fields.Many2one('purchase.order', string="Auto-Complete")

    #Field check k cho tạo addline khi hóa đơn đã có PO
    is_check = fields.Boolean()

    @api.constrains('exchange_rate')
    def _constrains_invoice_reference(self):
        for rec in self:
            if rec.exchange_rate < 0:
                raise ValidationError(_("Không được nhập số âm"))

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


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    type = fields.Selection(related="product_id.detailed_type")
    work_order = fields.Many2one('forlife.production', string='Work Order')
    current_user = fields.Many2one('res.users', default=lambda self: self.env.user, string='Account')
    uom_id = fields.Many2one(related="product_id.uom_id", string='Uom')
    warehouse = fields.Many2one('stock.location', string='Whs')
    discount = fields.Float(string='Taxs (%)')
    vat_tax = fields.Monetary(string='Taxs (Amount)')
    untaxed_amount = fields.Monetary(string='Untaxed Amount')
    tax_amount = fields.Monetary(string='Taxs Amount')
    total = fields.Monetary(string='Total')
    trade_discounts = fields.Float(string='Trade discounts')
    total_trade_discount = fields.Float(string='Total trade discount')

    ## fields common !!
    production_order = fields.Many2one('forlife.production', string='Production order')
    event_id = fields.Many2one('forlife.event', string='Program of events')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")

    ## goods invoice!!
    promotions = fields.Boolean(string='Promotions')
    quantity_purchased = fields.Char(string='Quantity Purchased', default=1)
    exchange_quantity = fields.Float(string='Exchange Quantity', default=1)
    vendor_price = fields.Float(string='Vendor Price')

    ## asset invoice!!
    asset_code = fields.Char('Asset Code')
    asset_name = fields.Char('Asset Name')
    code_tax = fields.Char(string='MST')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company.id)
    invoice_reference = fields.Char(string='Invoice Reference')
    invoice_description = fields.Char(string="Invoice Description")




