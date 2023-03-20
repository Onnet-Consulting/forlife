from odoo import api, fields, models, _


class ProductionOrder(models.Model):
    _name = 'production.order'
    _description = 'Attach Ingredients/Product Separation'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_tmpl_id'


    code = fields.Char('Reference')
    sequence = fields.Integer('Sequence')
    type = fields.Selection([
        ('normal', 'Attach Ingredients'),
        ('phantom', 'Product Separation')], 'BoM Type', default='normal', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', required=True)
    order_line_ids = fields.One2many('production.order.line', 'order_id', 'Production Order Lines')
    product_qty = fields.Float('Quantity', default=1.0, digits='Unit of Measure', required=True)

class ProductionOrderLine(models.Model):
    _name = 'production.order.line'
    _description = 'Production Order Line'

    product_id = fields.Many2one('product.product', 'Component', required=True)
    product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)
    sequence = fields.Integer('Sequence', default=1,)
    order_id = fields.Many2one('production.order', ondelete='cascade', required=True)
    attachments_count = fields.Integer('Attachments Count')