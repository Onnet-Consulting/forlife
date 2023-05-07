from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PointProductModelImport(models.Model):
    _name = 'point.product.model.import'

    _description = 'Sản phẩm tích điểm (Customize luồng import)'

    points_product_id = fields.Many2one('points.product', 'Nhóm sản phẩm')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    default_code = fields.Char('Mã nội bộ', related='product_id.default_code')
    point_addition = fields.Integer(string='Điểm cộng', related='points_product_id.point_addition')
    points_promotion_id = fields.Many2one('points.promotion', related='points_product_id.points_promotion_id')
    barcode = fields.Char('Mã vạch', related='product_id.barcode')

    _sql_constraints = [
        ('unique_product_id', 'UNIQUE(product_id, points_product_id)', 'Product must be unique!')
    ]

    @api.constrains('product_id')
    def check_constrains_product(self):
        list_invalid = []
        for rec in self:
            product_exist = rec.points_promotion_id.points_product_ids.filtered(lambda x: x.id != rec.points_product_id.id).product_ids.ids
            if rec.product_id.id in product_exist:
                # raise UserError(_('Sản phẩm '))
                list_invalid.append(rec.product_id.name)
        if len(list_invalid) > 0:
            raise UserError(_(f"Sản phẩm {', '.join(list_invalid)} đã tồn tại"))

    def name_get(self):
        return [(rec.id, '%s' % rec.product_id.name) for rec in self]

    def unlink(self):
        for rec in self:
            rec.points_product_id.product_ids = [(3, rec.product_id.id)]
        return super(PointProductModelImport, self).unlink()
