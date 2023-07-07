from odoo import api, fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    asset_group = fields.Boolean('Nhóm tài sản')
    structure_code = fields.Char('Mã kết cấu')
    old_name = fields.Char('Tên cũ')
    career_management = fields.Selection([('fashion','Fashion'), ('gdpk','GDPK')], string='Ngành hàng quản trị')