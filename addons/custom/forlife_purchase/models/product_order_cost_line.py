from odoo import fields, models, api


class PurchaseOrderCostLine(models.Model):
    _name = "purchase.order.cost.line"
    _description = 'Purchase Order Cost Line'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    transportation_costs_percent = fields.Float(string='% Transportation Costs')
    transportation_costs = fields.Float(string='Transportation Costs', compute='compute_transportation_costs')
    loading_costs_percent = fields.Float(string='% Loading Costs')
    loading_costs = fields.Float(string='Loading Costs', compute='compute_loading_costs')
    custom_costs_percent = fields.Float(string='% Custom Costs')
    custom_costs = fields.Float(string='Custom Costs', compute='compute_custom_costs')

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
