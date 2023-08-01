from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals_list):
        if not vals_list.get('barcode', False):
            if 'brand_id' in vals_list and 'attribute_line_ids' in vals_list and vals_list['brand_id'] and vals_list['attribute_line_ids']:
                attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
                rule = False
                for rec in vals_list['attribute_line_ids']:
                    if rec[2]['attribute_id'] == attribute_id.id:
                        rule = self.env['generate.rule'].search([('type_product_id', '=', rec[2]['value_ids'][0][2][0])], limit=1)
                        if rule:
                            break
                if not rule:
                    raise ValidationError(f"Không tìm thấy cấu hình sinh mã nào cho sản phẩm {vals_list['name']}")
                required_field_ids = rule.required_field_ids.mapped('name')
                for field in required_field_ids:
                    if field not in vals_list or vals_list[field] is False:
                        raise ValidationError(f"Thiếu trường bắt buộc {field} cho sản phẩm {vals_list['name']}!")
                attribute_required_ids = rule.attribute_required_ids.ids
                attrs_dict = self.convert_diff_attribute_line_to_dict(vals_list)
                if len(attribute_required_ids) > len(attrs_dict['attribute_id']):
                    raise ValidationError(f"Thiếu giá trị cho thuộc tính bắt buộc ở sản phẩm {vals_list['name']}")

                # if list_error_no_rule:
                #     raise ValidationError(_(f"Không tìm thấy cấu hình sinh mã nào cho sản phẩm {', '.join(list_error_no_rule)}"))
                # if list_error_no_reuired_field:
                #     raise ValidationError(_(f"Thiếu trường bắt buộc {field} cho sản phẩm {vals_list['name']}!"))
                # attribute_line = vals_list['attribute_line_ids'][0][2]
                # attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
                # if attribute_line['attribute_id'] == attribute_id.id:
                #     rule = self.env['generate.rule'].search([('type_product_id','=',attribute_line['value_ids'][0][2][0])])
                #     if rule:
        res = super(ProductTemplate, self).create(vals_list)
        return res

    def convert_diff_attribute_line_to_dict(self, vals_list):
        list_attribute_id = []
        list_value_id = []
        rslt = {}
        attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
        for rec in vals_list['attribute_line_ids']:
            if rec[2]['attribute_id'] != attribute_id.id:
                list_attribute_id.append(rec[2]['attribute_id'])
                list_value_id.append(rec[2]['value_ids'][0][2][0])
        rslt['attribute_id'] = list_attribute_id
        rslt['value_id'] = list_value_id
        return rslt