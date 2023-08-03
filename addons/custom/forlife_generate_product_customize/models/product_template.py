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
                list_field_invalid = []

                for field in required_field_ids:
                    if field not in vals_list or vals_list[field] is False:
                        current_model_id = self.env['ir.model'].search([('model', '=', self._name)])
                        model_field = self.env['ir.model.fields'].search([('name', '=', field), ('model_id', '=', current_model_id.id)])
                        list_field_invalid.append(model_field.field_description)
                if list_field_invalid:
                    raise ValidationError(f"""Thiếu trường bắt buộc "{', '.join(list_field_invalid)}" cho sản phẩm {vals_list['name']}!""")

                attribute_required_ids = rule.attribute_required_ids.ids
                attrs_dict_invals = self.convert_diff_attribute_line_to_dict(vals_list, check_sku=False)
                if len(attribute_required_ids) > len(attrs_dict_invals['attribute_id']):
                    # Find Difference between two lists
                    set_diff = set(attribute_required_ids).symmetric_difference(set(attrs_dict_invals['attribute_id']))
                    name_of_attrs = rule.attribute_required_ids.filtered(lambda x: x.id in list(set_diff)).mapped('name')
                    raise ValidationError(f"Thiếu giá trị cho thuộc tính bắt buộc {', '.join(name_of_attrs)} cho sản phẩm {vals_list['name']}")
                self.generate_new_sku(vals_list, rule)

        res = super(ProductTemplate, self).create(vals_list)
        return res

    def generate_new_sku(self, vals_list, rule):
        if not vals_list.get('sku_code', False):
            attribute_check_sku_ids = rule.attribute_check_sku_ids.ids
            sku_field_check_ids = rule.sku_field_check_ids.ids
            print(attribute_check_sku_ids)
            attrs_dict_invals = self.convert_diff_attribute_line_to_dict(vals_list, check_sku=True)
            # p_check_sku = self.env['product.template.attribute.line'].sudo().search([('attribute_id','in', attribute_check_sku_ids)], limit=1)
            # if not p_exits:
            #     pass




    def convert_diff_attribute_line_to_dict(self, vals_list, check_sku):
        list_attribute_id, list_value_id = [], []
        rslt = {}
        attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
        for rec in vals_list['attribute_line_ids']:
            if rec[2]['attribute_id'] != attribute_id.id and not check_sku:
                list_attribute_id.append(rec[2]['attribute_id'])
                list_value_id.append(rec[2]['value_ids'][0][2][0])
            else:
                list_attribute_id.append(rec[2]['attribute_id'])
                list_value_id.append(rec[2]['value_ids'][0][2][0])
        rslt['attribute_id'] = list_attribute_id
        rslt['value_id'] = list_value_id
        return rslt