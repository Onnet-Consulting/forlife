from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    description_color = fields.Char('Mô tả màu')
    material_composition = fields.Char('Thành phần chất liệu')
    cloth_code = fields.Char('Mã vải')
    collection = fields.Char('Bộ sưu tập')
    user_manual = fields.Char('Hướng dẫn sử dụng')
    note = fields.Text('Ghi chú')
    daisai = fields.Char('Dải size')
    date_start_business = fields.Date(string='Thời điểm bắt đầu kinh doanh')
    date_end_business = fields.Date(string='Thời điểm kết thúc kinh doanh')