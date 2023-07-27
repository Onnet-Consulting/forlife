from odoo import fields, api, models


class InheritPosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    promotion_string_code = fields.Char(string='CTKM', compute='get_code_promotion_code')
    product_barcode = fields.Char(related='product_id.barcode', string='Mã vạch')
    product_name = fields.Char(related='product_id.name', string='Tên sản phẩm')
    total_amount_discount = fields.Float(compute='compute_total_amount_discount')

    @api.depends('discount_details_lines.money_reduced')
    def compute_total_amount_discount(self):
        for rec in self:
            rec.total_amount_discount = sum(rec.discount_details_lines.mapped('money_reduced'))

    @api.depends('promotion_usage_ids.program_id')
    def get_code_promotion_code(self):
        for rec in self:
            rec.promotion_string_code = ''
            program = rec.promotion_usage_ids.mapped('program_id.code')
            if program:
                rec.promotion_string_code = ','.join(x if x else '' for x in program)
