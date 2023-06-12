from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class QuantityProductionOrder(models.Model):
    _name = 'quantity.production.order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Quantity Production Order"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    location_id = fields.Many2one('stock.location', "Source Location",)
    production_id = fields.Many2one('forlife.production', string='Forlife Production')
    quantity = fields.Integer(string='Quantity')
    quantity_order_line = fields.Many2many('purchase.order.line')
