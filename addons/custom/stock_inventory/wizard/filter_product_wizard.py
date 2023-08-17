# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json
from odoo.tools.safe_eval import safe_eval


class FilterProductWizard(models.Model):
    _name = 'filter.product.wizard'
    _inherit = 'report.base'
    _description = 'Lọc sản phẩm'
    _order = 'id desc'

    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    category_type_ids = fields.Many2many('product.category.type', 'filter_product_wizard_cate_type_rel', string="Type of Product Category")
    product_brand_ids = fields.Many2many('product.category', 'filter_product_wizard_brand_rel', string='Level 1')
    product_group_ids = fields.Many2many('product.category', 'filter_product_wizard_group_rel', string='Level 2')
    product_line_ids = fields.Many2many('product.category', 'filter_product_wizard_line_rel', string='Level 3')
    texture_ids = fields.Many2many('product.category', 'filter_product_wizard_texture_rel', string='Level 4')
    category_domain = fields.Char('Products', compute='_compute_category_domain')

    category_type_id = fields.Integer()
    product_brand_id = fields.Integer()

    @api.onchange('category_type_ids')
    def onchange_category_type(self):
        self.product_brand_ids = self.product_brand_ids.filtered(lambda f: f.category_type_id.id in self.category_type_ids.ids)

    @api.depends('category_type_id', 'product_brand_ids', 'product_group_ids', 'product_line_ids', 'texture_ids')
    def _compute_category_domain(self):
        Utility = self.env['res.utility']
        for line in self:
            category_domain = [('type', '=', 'product')]
            categ_ids = line.texture_ids or line.product_line_ids or line.product_group_ids or line.product_brand_ids
            if categ_ids:
                category_domain += [('categ_id', 'in', Utility.get_all_category_last_level(categ_ids))]
            line.category_domain = json.dumps(category_domain)

    @api.onchange('product_brand_ids')
    def onchange_product_brand(self):
        self.product_group_ids = self.product_group_ids.filtered(lambda f: f.parent_id.id in self.product_brand_ids.ids)

    @api.onchange('product_group_ids')
    def onchange_product_group(self):
        self.product_line_ids = self.product_line_ids.filtered(lambda f: f.parent_id.id in self.product_group_ids.ids)

    @api.onchange('product_line_ids')
    def onchange_product_line(self):
        self.texture_ids = self.texture_ids.filtered(lambda f: f.parent_id.id in self.product_line_ids.ids)

    def action_confirm(self):
        self.inventory_id.product_ids = self.env['product.product'].search(safe_eval(self.category_domain or "[('id', '=', 0)]"))

    def get_filename(self):
        return f"PKK {self.inventory_id.warehouse_id.name or ''} {self.inventory_id.date.strftime('%d%m%Y')}"

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('PKK')
        sheet.freeze_panes(1, 0)
        sheet.set_row(0, 30)
        TITLES = [
            'STT', 'MÃ HÀNG', 'TÊN HÀNG', 'MÀU', 'SIZE', 'NHÓM SẢN PHẨM', 'ĐƠN VỊ', 'TỒN PHẦN MỀM',
            'SL xác nhận lần 1', 'Chênh lệch lần 1', 'SL xác nhận lần 2', 'Chênh lệch lần 2']
        for idx, title in enumerate(TITLES):
            sheet.write(0, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES) - 1, 20)
        attr_codes = self.env['res.utility'].get_attribute_code_config()
        attr_values = self.env['res.utility'].get_attribute_value_by_product_id(product_ids=self.inventory_id.line_ids.product_id.ids)
        row = 1
        stt = 1
        for line in self.inventory_id.line_ids:
            product_attr_value = attr_values.get(str(line.product_id.id)) or {}
            mau = product_attr_value.get(attr_codes.get('mau_sac')) or []
            size = product_attr_value.get(attr_codes.get('size')) or []
            sheet.write(row, 0, stt, formats.get('center_format'))
            sheet.write(row, 1, line.product_id.barcode or '', formats.get('normal_format'))
            sheet.write(row, 2, line.product_id.name or '', formats.get('normal_format'))
            sheet.write(row, 3, ','.join(mau) or '', formats.get('normal_format'))
            sheet.write(row, 4, ','.join(size) or '', formats.get('normal_format'))
            sheet.write(row, 5, line.product_id.categ_id.complete_name or '', formats.get('normal_format'))
            sheet.write(row, 6, line.product_id.uom_id.name or '', formats.get('normal_format'))
            sheet.write(row, 7, line.theoretical_qty or 0, formats.get('int_number_format'))
            sheet.write(row, 8, line.x_first_qty, formats.get('int_number_format'))
            sheet.write(row, 9, line.difference_qty1, formats.get('int_number_format'))
            sheet.write(row, 10, line.product_qty, formats.get('int_number_format'))
            sheet.write(row, 11, line.difference_qty, formats.get('int_number_format'))
            row += 1
            stt += 1
