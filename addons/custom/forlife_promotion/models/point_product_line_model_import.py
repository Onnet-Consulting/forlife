from odoo import api, fields, models

class PointProductLineModelImport(models.Model):
    _name = 'point.product.line.model.import'

    _description = 'Sản phẩm tích điểm sự kiện (Customize luồng import)'

    # points_product_line_id = fields.Many2one('points.product.line')
    # product_id = fields.Many2one('product.product', 'Sản phẩm')
    # default_code = fields.Char('Mã nội bộ', related='product_id.default_code')
    # point_addition = fields.Integer(string='Điểm cộng', related='points_product_line_id.point_addition')
    # event_id = fields.Many2one('event', related='points_product_line_id.event_id')
    #
    # _sql_constraints = [
    #     ('unique_product_id', 'UNIQUE(product_id, points_product_line_id)', 'Product must be unique!')
    # ]
    #
    # def name_get(self):
    #     return [(rec.id, '%s' % rec.product_id.name) for rec in self]
    #
    #
    # def unlink(self):
    #     for rec in self:
    #         rec.points_product_line_id.product_ids = [(3, rec.product_id.id)]
    #     return super(PointProductLineModelImport, self).unlink()