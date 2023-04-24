from odoo import api, fields, models

class PointProductModelImport(models.Model):
    _name = 'point.product.model.import'

    _description = 'Sản phẩm tích điểm (Customize luồng import)'

    points_product_id = fields.Many2one('points.product', 'Nhóm sản phẩm')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    default_code = fields.Char('Mã nội bộ', related='product_id.default_code')
    point_addition = fields.Integer(string='Điểm cộng', related='points_product_id.point_addition')
    points_promotion_id = fields.Many2one('points.promotion', related='points_product_id.points_promotion_id')

    _sql_constraints = [
        ('unique_product_id', 'UNIQUE(product_id, points_product_id)', 'Product must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.product_id.name) for rec in self]

    @api.model_create_multi
    def create(self, vals_list):
        for idx, line in enumerate(vals_list):
            if ('active_model' in self._context and self._context.get('active_model')) and ('active_id' in self._context and self._context.get('active_id')):
                points_product = self.env['points.product'].sudo().search([('id','=',int(self._context.get('default_points_product_id')))])
                points_product.product_ids = [(4, int(vals_list[idx]['product_id']))]
        return super(PointProductModelImport, self).create(vals_list)

    def unlink(self):
        for rec in self:
            rec.points_product_id.product_ids = [(3, rec.product_id.id)]
        return super(PointProductModelImport, self).unlink()
