from odoo import api, fields, models,_

class Product(models.Model):
    _inherit = 'product.product'

    # is_split_product = fields.Boolean('Là sản phẩm phân tách')
    split_product_id = fields.Many2one('split.product.line.sub')