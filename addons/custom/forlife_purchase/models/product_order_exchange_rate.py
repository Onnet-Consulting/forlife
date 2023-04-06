from odoo import fields, models, api


class PurchaseOrderExchangeRate(models.Model):
    _name = "purchase.order.exchange.rate"
    _description = 'Purchase Order Exchange Rate'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')

    usd_amount = fields.Float(string='USD Amount')  # đây chính là cột Thành tiền bên tab Sản phầm, a Trung đã viết trước
    vnd_amount = fields.Float(string='VND Amount', compute='compute_vnd_amount', store=1)

    import_tax = fields.Float(string='Import Tax')
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_amount', store=1)

    special_consumption_tax = fields.Float(string='% Special Consumption Tax')
    special_consumption_tax_amount = fields.Float(string='Special Consumption Tax', compute='_compute_special_consumption_tax_amount', store=1)

    vat_tax = fields.Float(string='% VAT')
    vat_tax_amount = fields.Float(string='VAT', compute='_compute_vat_tax_amount', store=1)

    # total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Total Tax Amount', compute='compute_tax_amount', store=1)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.depends('usd_amount', 'purchase_order_id.exchange_rate')
    def compute_vnd_amount(self):
        for rec in self:
            rec.vnd_amount = rec.usd_amount * rec.purchase_order_id.exchange_rate

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


