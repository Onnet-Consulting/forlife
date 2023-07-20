from odoo import api, fields, models

class Product(models.Model):
    _inherit = 'product.template'

    tolerance = fields.Float('Tolerance')
    tolerance_ids = fields.One2many('product.tolerance.line', 'product_id', string='Supplier Tolerance')
    sku_code = fields.Char('Mã SKU')
    default_code = fields.Char(string='Mã hiển thị')
    special_group_product = fields.Char('Nhóm sản phẩm đặc trưng')
    stamp = fields.Char('Tem nhãm')
    heso = fields.Float('Hệ số quy đổi')
    trongluong = fields.Float('Trọng lượng')
    kichthuoc = fields.Float('Kích thước')
    khovai = fields.Char('Khổ vải')
    pantone = fields.Char('Pantone')
    mau_ncc = fields.Char('Màu NCC')
    ma_sp_ncc = fields.Char('Mã sản phẩm nhà cung cấp')
    tenhangcu = fields.Char('Tên hàng cũ')
    makithuat = fields.Char('Mã kĩ thuật')
    code_design = fields.Char('Mã thiết kế')
    group_row_1 = fields.Char('Nhóm hàng 1')
    line_row_1 = fields.Char('Dòng hàng 1')
    structure = fields.Char('Kết cấu 1')

    @api.onchange('detailed_type')
    def onchange_detailed_type(self):
        if self.detailed_type == 'asset':
            return {'domain': {'categ_id': [('asset_group', '=', True)]}}
        else:
            return {'domain': {'categ_id': [('asset_group', '=', False)]}}
