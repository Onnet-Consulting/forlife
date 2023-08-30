from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplateAttrLine(models.Model):
    _inherit = 'product.template.attribute.line'

    @api.constrains('attribute_id', 'value_ids')
    def contraints_same_value(self):
        for rec in self:
            exits = self.search([('attribute_id', '=', rec.attribute_id.id),('id','!=',rec.id),('product_tmpl_id','=',rec.product_tmpl_id.id)], limit=1)
            if exits:
                if rec.attribute_id.id == exits.attribute_id.id:
                    raise ValidationError('Đã tồn tại giá trị của thuộc tính %s và sản phẩm %s!' % (rec.attribute_id.name, rec.product_tmpl_id.name))
            if len(rec.value_ids) > 1 and rec.attribute_id.attrs_code != 'AT038':
                raise ValidationError('Chỉ được một giá trị cho một thuộc tính!')

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    number_related_products = fields.Integer(compute='_compute_number_related_products', store=True)

    def action_open_related_products(self):
        pass
