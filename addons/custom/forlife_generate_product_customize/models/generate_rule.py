from odoo import models, fields, _


class GenerateRule(models.Model):
    _name = 'generate.rule'

    _description = 'Generate Rule Product'

    name = fields.Char('Đầu mã')

    def domain_for_type_product(self):
        value = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
        if value:
            attr_ids = value.value_ids.ids
            return f"[('id','in', {attr_ids})]"
        return "[]"

    def domain_for_attribute_required(self):
        value = self.env['product.attribute'].sudo().search([('attrs_code', '=', 'AT027')], limit=1)
        if value:
            return f"[('id','!=', {value.id})]"
        return "[]"
    type_product_id = fields.Many2one('product.attribute.value', 'Loại hàng hóa', domain=domain_for_type_product)

    brand_id = fields.Many2one('res.brand', 'Thương hiệu')

    attribute_required_ids = fields.Many2many('product.attribute', 'attribute_required_rel', 'generate_rule_1_id', 'attribute_id', string='Thuộc tính bắt buộc', domain=domain_for_attribute_required)

    attribute_check_sku_ids = fields.Many2many('product.attribute', 'attribute_check_sku_rel', 'generate_rule_2_id', 'attribute_check_sku_id',
                                               string='Thuộc tính check SKU')

    attribute_check_barcode_ids = fields.Many2many('product.attribute', 'attribute_check_barcode_rel','generate_rule_3_id', 'attribute_check_barcode_id', string='Thuộc tính check Barcode')

    required_field_ids = fields.Many2many('ir.model.fields', 'required_field_rel', 'generate_rule_4_id', 'required_field_id', string='Trường bắt buộc', domain=[('model','in',['product.template'])])

    sku_field_check_ids = fields.Many2many('ir.model.fields', 'sku_field_check_rel', 'generate_rule_5_id', 'sku_field_check_id', string='Trường check SKU',domain=[('model','in',['product.template'])])

    barcode_field_check_ids = fields.Many2many('ir.model.fields', 'barcode_field_check_rel', 'generate_rule_6_id', 'barcode_field_check_id', string='Trường check Barcode',domain=[('model','in',['product.template'])])
