from odoo import fields, models, api


class PurchaseOrderCostLine(models.Model):
    _name = "purchase.order.cost.line"
    _description = 'Purchase Order Cost Line'

    product_id = fields.Many2one('product.product', string='Sản phẩm', domain=[('detailed_type', '=', 'service')])
    name = fields.Char(string='Mô tả', related='product_id.name')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=1)
    exchange_rate = fields.Float(string='Tỷ giá', default=1)
    foreign_amount = fields.Float(string='Tổng tiền ngoại tệ̣')
    vnd_amount = fields.Float(string='Chi phí VND ước tính', compute='compute_vnd_amount', store=1, readonly=False)
    is_check_pre_tax_costs = fields.Boolean('Chi phí trước thuế VND')
    actual_cost = fields.Float(string='Chi phí thực tế', copy=False)
    cost_paid = fields.Float(string='Chi phí đã lên hóa đơn', compute='compute_cost_paid', copy=False)
    company_currency = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)

    @api.depends('vnd_amount', 'purchase_order_id.count_invoice_inter_expense_fix')
    def compute_cost_paid(self):
        for rec in self:
            domain = [
                ('purchase_order_product_id', 'in', rec.purchase_order_id.ids),
                ('move_type', '=', 'in_invoice'),
                ('select_type_inv', '=', 'expense'),
                ('state', '=', 'posted'),
            ]
            invoices = self.env['account.move'].search(domain)
            cost_paid = 0
            for detail_id in invoices.account_expense_labor_detail_ids.filtered(lambda x: x.product_id.id == rec.product_id.id):
                cost_paid += (detail_id.totals_back * detail_id.move_id.exchange_rate) / (rec.exchange_rate or 1)
            rec.cost_paid = cost_paid

    @api.onchange('currency_id')
    def onchange_exchange_rate(self):
        if self.currency_id:
            self.exchange_rate = self.currency_id.inverse_rate

    @api.depends('exchange_rate', 'foreign_amount')
    def compute_vnd_amount(self):
        for rec in self:
            rec.vnd_amount = rec.exchange_rate * rec.foreign_amount

