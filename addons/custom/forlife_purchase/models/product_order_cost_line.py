from odoo import fields, models, api


class PurchaseOrderCostLine(models.Model):
    _name = "purchase.order.cost.line"
    _description = 'Purchase Order Cost Line'

    product_id = fields.Many2one('product.product', string='Sản phẩm',required=True)
    name = fields.Char(string='Mô tả', related='product_id.name',required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',required=True)
    expensive_total = fields.Float(string='Tổng tiền',)
    dollars_money = fields.Float(string='Tiền USD')

    @api.onchange('purchase_order_id', 'purchase_order_id.exchange_rate', 'dollars_money')
    def onchange_expensive_total(self):
        self.expensive_total = self.dollars_money * self.purchase_order_id.exchange_rate

