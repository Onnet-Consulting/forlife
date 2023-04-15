from odoo import fields, models, api


class PurchaseOrderCostLine(models.Model):
    _name = "purchase.order.cost.line"
    _description = 'Purchase Order Cost Line'

    product_id = fields.Many2one('product.product', string='Sản phẩm')
    name = fields.Char(string='Mô tả', related='product_id.name')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    transportation_costs_percent = fields.Float(string='% Chi phí vận chuyển')
    transportation_costs = fields.Float(string='Chi phí vận chuyển', compute='compute_transportation_costs')
    loading_costs_percent = fields.Float(string='% Chi phí bốc dỡ')
    loading_costs = fields.Float(string='Chi phí bốc dỡ ', compute='compute_loading_costs')
    custom_costs_percent = fields.Float(string='% Chi phí thông quan')
    custom_costs = fields.Float(string='Chi phí thông quan', compute='compute_custom_costs')

    @api.depends('purchase_order_id.transportation_total', 'transportation_costs_percent')
    def compute_transportation_costs(self):
        for rec in self:
            rec.transportation_costs = rec.purchase_order_id.transportation_total * rec.transportation_costs_percent

    @api.depends('purchase_order_id.loading_total', 'loading_costs_percent')
    def compute_loading_costs(self):
        for rec in self:
            rec.loading_costs = rec.purchase_order_id.loading_total * rec.loading_costs_percent

    @api.depends('purchase_order_id.custom_total', 'custom_costs_percent')
    def compute_custom_costs(self):
        for rec in self:
            rec.custom_costs = rec.purchase_order_id.custom_total * rec.custom_costs_percent
