from odoo import api, fields, models

class PointProductModelImport(models.Model):
    _name = 'point.product.model.import'

    _description = 'Sản phẩm tích điểm (Customize luồng import)'

    points_product_id = fields.Many2one('points.product', 'Nhóm sản phẩm')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    default_code = fields.Char('Mã nội bộ', related='product_id.default_code')
    point_addition = fields.Integer(string='Điểm cộng', related='points_product_id.point_addition')

