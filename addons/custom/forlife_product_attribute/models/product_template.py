from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplateAttrLine(models.Model):
    _inherit = 'product.template.attribute.line'

    @api.constrains('attribute_id', 'value_ids')
    def contraints_same_value(self):
        for rec in self:
            exits = self.search([('attribute_id', '=', rec.attribute_id.id),('id','!=',rec.id),('product_tmpl_id','=',rec.product_tmpl_id.id)], limit=1)
            if rec.value_ids[0] == exits.value_ids[0]:
                raise ValidationError('Đã tồn tại giá trị của thuộc tính này!')
            if len(rec.value_ids) > 1:
                raise ValidationError('Chỉ được một giá trị cho một thuộc tính!')



