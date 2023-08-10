from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import math


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals_list):
        if ('barcode' not in vals_list or ('barcode' in vals_list and vals_list['barcode'] is False)) and (
                'sku_code' not in vals_list or ('sku_code' in vals_list and vals_list['sku_code'] is False)):
            if 'brand_id' in vals_list and 'attribute_line_ids' in vals_list and vals_list['brand_id'] and vals_list['attribute_line_ids']:
                attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
                rule = False

                for rec in vals_list['attribute_line_ids']:
                    if rec[2]['attribute_id'] == attribute_id.id:
                        rule = self.env['generate.rule'].search([('type_product_id', '=', rec[2]['value_ids'][0][2][0]), ('brand_id', '=', vals_list['brand_id'])],
                                                                limit=1)
                        if rule:
                            break
                if not rule:
                    raise ValidationError(f"Không tìm thấy cấu hình sinh mã nào cho sản phẩm {vals_list['name']}")
                # kiem tra truong bat buoc
                self.validate_required_field(rule, vals_list)
                # kiểm tra thuộc tinh bắt buoc
                self.validate_attr_required(rule, vals_list)
                # kiem tra field check create SKU Barcode
                res = super(ProductTemplate, self).create(vals_list)
                # kiem tra thuoc tinh check create sku
                pmtl_attr_exits = self.sudo().search(
                    [('attribute_check_text', '=', res.attribute_check_text), ('id', '!=', res.id), ('attribute_check_text', '!=', False)], limit=1)
                if pmtl_attr_exits:
                    raise ValidationError(_(f"Bị trùng thông tin trường hoặc thuộc tính check tạo SKU trong sản phẩm {res.name}!"))
                if 'test_import' not in self._context or not self._context.get('test_import'):
                    sku_code = self.generate_sku(rule)
                    barcode = self.generate_ean_barcode(rule, sku_code)
                    res.sku_code = sku_code
                    res.barcode = barcode
                return res
        if 'sku_code' in vals_list and vals_list['sku_code'] and ('barcode' not in vals_list or ('barcode' in vals_list and vals_list['barcode'] is False)):
            old_sku = self.env['product.template'].sudo().search([('sku_code', '=', vals_list['sku_code'])], limit=1)
            if not old_sku:
                raise ValidationError(f"Chưa tồn tại sản phẩm nào có cùng SKU cho sản phẩm {vals_list['name']}")
            if old_sku:
                res = super(ProductTemplate, self).create(vals_list)
                if not res.rule_id:
                    raise ValidationError(f"Không tìm thấy cấu hình sinh mã nào cho sản phẩm {res.name}")
                self.validate_required_field(res.rule_id, vals_list)
                # kiểm tra thuộc tinh bắt buoc
                self.validate_attr_required(res.rule_id, vals_list)
                if res.attribute_check_text != old_sku.attribute_check_text:
                    raise ValidationError(f"Chưa đúng thông tin SKU cho sản phẩm {res.name}")
                else:
                    barcode_att_and_check = self.env['product.template'].search([('att_and_field_barcode','=', res.att_and_field_barcode),('id','!=', res.id)], limit=1)
                    if barcode_att_and_check:
                        raise ValidationError(f"Bị trùng thông tin thuộc tính check Barcode sản phẩm {res.name}")
                if 'test_import' not in self._context or not self._context.get('test_import'):
                    barcode = self.generate_ean_barcode(rule=res.rule_id, sku_code=vals_list['sku_code'])
                    res.barcode = barcode
                return res
        return super(ProductTemplate, self).create(vals_list)

    att_and_field_barcode = fields.Text(compute='_compute_att_and_field_barcode', store=True)

    @api.depends('rule_id', 'attribute_line_ids')
    def _compute_att_and_field_barcode(self):
        for rec in self:
            if rec.rule_id:
                att_check_barcode_ids = rec.rule_id.attribute_check_barcode_ids.ids
                fields_check = rec.rule_id.barcode_field_check_ids.mapped('name')
                sql = f"""SELECT {', '.join(fields_check)} FROM product_template WHERE id = {rec.id}"""
                self._cr.execute(sql)
                data = self._cr.dictfetchall()
                attribute_line_id = rec.attribute_line_ids.mapped('attribute_id.id')
                set_same = list(set(att_check_barcode_ids) & set(attribute_line_id))
                attr_id_not_in_vals_list = []
                for x in att_check_barcode_ids:
                    if x not in attribute_line_id:
                        attr_id_not_in_vals_list.append('false')
                string_field = []
                for r in sorted(rec.attribute_line_ids):
                    if r.attribute_id.id in set_same:
                        string_field.append(f"{r.attribute_id.name}-{r.value_ids[0].name}")
                stringfield = ':'.join(string_field)
                if attr_id_not_in_vals_list:
                    rec.att_and_field_barcode = f"{rec.brand_id.name}-{rec.rule_id.type_product_id.name}-{stringfield}-{str(data)}-{':'.join(attr_id_not_in_vals_list)}"
                else:
                    rec.att_and_field_barcode = f"{rec.brand_id.name}-{rec.rule_id.type_product_id.name}-{str(data)}-{stringfield}"
            else:
                rec.att_and_field_barcode = False

        # @api.constrains('attribute_check_text')
    # def contrainst_attribute_rule_create_barcode(self):
    #     for rec in self:
    #         pmtl_attr_exits = self.sudo().search([('attribute_check_text', '=', rec.attribute_check_text), ('id', '!=', rec.id),('attribute_check_text','!=', False)], limit=1)
    #         if pmtl_attr_exits:
    #             raise ValidationError(_(f"Bị trùng thông tin thuộc tính check tạo SKU trong sản phẩm {rec.name}!"))

    def generate_ean_barcode(self, rule, sku_code):
        first_char = rule.name[0]
        sku_code = sku_code
        sequence_for_sku = self.env['ir.sequence'].search([('sku_code', '=', sku_code)], limit=1)
        if sequence_for_sku:
            sequence = self.env['ir.sequence'].next_by_code(f"{sequence_for_sku.code}")
        else:
            sequence = self.env['ir.sequence'].create({
                'name': f'BARCODE SEQUENCE {sku_code}',
                'sku_code': sku_code,
                'code': f"product.template.{sku_code}",
                'active': True,
                'padding': 3,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False
            })
            sequence = self.env['ir.sequence'].next_by_code(f"{sequence.code}")
            # self.env['ir.sequence'].next_by_code('product.template.barcode') or ''
        barcode = first_char + str(sku_code) + str(sequence)
        ean = self.return_ean(barcode)
        return barcode + ean

    def return_ean(self, barcode):
        res = list(map(int, str(barcode)))
        res.append(0)
        res.reverse()

        sum_odd_positions = 0
        for i in range(1, len(res), 2):
            sum_odd_positions += res[i]
        b2 = sum_odd_positions * 3

        sum_even_positions = 0
        for i in range(0, len(res), 2):
            sum_even_positions += res[i]
        total = b2 + sum_even_positions
        check = int(10 - math.ceil(total % 10.0)) % 10
        return str(check)

    def generate_sku(self, rule):
        second_char = rule.name[1]
        sequence = self.env['ir.sequence'].next_by_code('product.template.sku') or ''
        return second_char + str(sequence)

    def validate_attr_required(self, rule, vals_list):
        attribute_required_ids = rule.attribute_required_ids.ids
        attrs_dict_invals = self.convert_diff_attribute_line_to_dict(vals_list, check_sku=False)
        name_of_attrs = []
        for x in attribute_required_ids:
            if x not in attrs_dict_invals['attribute_id']:
                name_of_attrs.append(x)
        if name_of_attrs:
            raise ValidationError(f"Thiếu giá trị cho thuộc tính bắt buộc {', '.join(name_of_attrs)} cho sản phẩm {vals_list['name']}")

    def validate_required_field(self, rule, vals_list):
        required_field_ids = rule.required_field_ids.mapped('name')
        list_field_invalid = []
        if required_field_ids and vals_list:
            for field in required_field_ids:
                if field not in vals_list or vals_list[field] is False:
                    current_model_id = self.env['ir.model'].search([('model', '=', self._name)])
                    model_field = self.env['ir.model.fields'].search([('name', '=', field), ('model_id', '=', current_model_id.id)])
                    list_field_invalid.append(model_field.field_description)
            if list_field_invalid:
                raise ValidationError(f"""Thiếu trường bắt buộc "{', '.join(list_field_invalid)}" cho sản phẩm {vals_list['name']}!""")

    def validate_field_check_create(self, rule, vals_list):
        fields_check = rule.barcode_field_check_ids.mapped('name')
        value_field_dict = {}
        if fields_check:
            for field in fields_check:
                if field in vals_list:
                    value_field_dict[f"product_tmpl_id.{field}"] = vals_list[field]
                else:
                    value_field_dict[f"product_tmpl_id.{field}"] = False
        output_list = []
        for key, val in value_field_dict.items():
            output_list.append(tuple((key, '=', val)))
        output_list.append(tuple(('product_tmpl_id.rule_id', '=', rule.id)))
        return output_list

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

    rule_id = fields.Many2one('generate.rule', compute='compute_rule', store=True)

    @api.depends('attribute_line_ids', 'brand_id')
    def compute_rule(self):
        attribute_id = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
        for rec in self:
            if rec.brand_id and rec.attribute_line_ids:
                att = rec.attribute_line_ids.filtered(lambda x: x.attribute_id.id == attribute_id.id)
                if att and att.value_ids[0]:
                    value_id = att.value_ids[0].id
                    if value_id:
                        rule_sku = self.env['generate.rule'].search([('type_product_id', '=', value_id), ('brand_id', '=', rec.brand_id.id)], limit=1)
                        if rule_sku:
                            rec.rule_id = rule_sku.id
                        else:
                            rec.rule_id = False
                else:
                    rec.rule_id = False
            else:
                rec.rule_id = False

    attribute_check_text = fields.Text(compute='_compute_attribute_value', store=True)

    @api.depends('rule_id', 'attribute_line_ids')
    def _compute_attribute_value(self):
        for rec in self:
            if rec.rule_id:
                att_check_sku_ids = rec.rule_id.attribute_check_sku_ids.ids
                fields_check = rec.rule_id.sku_field_check_ids.mapped('name')
                sql = f"""SELECT {', '.join(fields_check)} FROM product_template WHERE id = {rec.id}"""
                self._cr.execute(sql)
                data = self._cr.dictfetchall()
                attribute_line_id = rec.attribute_line_ids.mapped('attribute_id.id')
                set_same = list(set(att_check_sku_ids) & set(attribute_line_id))
                attr_id_not_in_vals_list = []
                for x in att_check_sku_ids:
                    if x not in attribute_line_id:
                        attr_id_not_in_vals_list.append('false')
                string_field = []
                for r in sorted(rec.attribute_line_ids):
                    if r.attribute_id.id in set_same:
                        string_field.append(f"{r.attribute_id.name}-{r.value_ids[0].name}")
                stringfield = ':'.join(string_field)
                if attr_id_not_in_vals_list:
                    rec.attribute_check_text = f"{rec.brand_id.name}-{rec.rule_id.type_product_id.name}-{stringfield}-{str(data)}-{':'.join(attr_id_not_in_vals_list)}"
                else:
                    rec.attribute_check_text = f"{rec.brand_id.name}-{rec.rule_id.type_product_id.name}-{str(data)}-{stringfield}"
            else:
                rec.attribute_check_text = False
