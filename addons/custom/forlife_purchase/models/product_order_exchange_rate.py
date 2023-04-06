from odoo import fields, models, api


class PurchaseOrderExchangeRate(models.Model):
    _name = "purchase.order.exchange.rate"
    _description = 'Purchase Order Exchange Rate'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    usd_amount = fields.Float(string='USD Amount')
    vnd_amount = fields.Float(string='VND Amount', compute='compute_vnd_amount')
    import_tax = fields.Float(string='Import Tax')
    tax_amount = fields.Float(string='Tax Amount', compute='compute_tax_amount')
    total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Total Tax Amount', compute='compute_tax_amount')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.depends('tax_amount', 'usd_amount', 'purchase_order_id.exchange_rate')
    def compute_vnd_amount(self):
        for rec in self:
            rec.vnd_amount = rec.usd_amount * rec.purchase_order_id.exchange_rate
            rec.total_vnd_amount = rec.vnd_amount + rec.tax_amount

    @api.depends('import_tax', 'vnd_amount')
    def compute_tax_amount(self):
        for rec in self:
            rec.tax_amount = rec.vnd_amount * rec.import_tax * 0.01
            rec.total_tax_amount = rec.tax_amount


