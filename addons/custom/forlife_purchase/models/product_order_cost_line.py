from odoo import fields, models, api


class PurchaseOrderCostLine(models.Model):
    _name = "purchase.order.cost.line"
    _description = 'Purchase Order Cost Line'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    usd_amount = fields.Float(string='USD Amount')
    vnd_amount = fields.Float(string='VND Amount')
    hidden_amount = fields.Float(string='', compute='compute_vnd_amount')
    allocate = fields.Float(string='Allocate')
    amt_allocate = fields.Float(string='Amt Allocate', compute='compute_amt_allocate')
    total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_amt_allocate = fields.Float(string='Total Amt Allocate', compute='compute_amt_allocate')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.depends('amt_allocate', 'usd_amount', 'purchase_order_id.exchange_rate')
    def compute_vnd_amount(self):
        for rec in self:
            rec.hidden_amount = rec.usd_amount * rec.purchase_order_id.exchange_rate
            rec.total_vnd_amount = rec.vnd_amount + rec.amt_allocate

    @api.depends('allocate', 'vnd_amount')
    def compute_amt_allocate(self):
        for rec in self:
            rec.amt_allocate = rec.vnd_amount * rec.allocate * 0.01
            rec.total_amt_allocate = rec.amt_allocate

    @api.model
    def create(self, vals):
        line = super(PurchaseOrderCostLine, self).create(vals)
        if line.hidden_amount:
            line.write({'vnd_amount': line.hidden_amount})
        return line
