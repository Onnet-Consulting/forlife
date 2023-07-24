from odoo import fields, models, api
from datetime import datetime


class ProductionHistory(models.Model):
    _name = "production.history"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Production History"
    _order = 'create_date desc'
    _rec_name = 'code'

    version = fields.Char(string="Version", default="New", copy=False)
    code = fields.Char("Lệnh sản xuất")
    name = fields.Char("Tên lệnh sản xuất")
    user_id = fields.Many2one('res.users', string="Người tạo")
    company_id = fields.Many2one('res.company', string='Công ty')
    created_date = fields.Date(string="Ngày tạo")
    implementation_id = fields.Many2one('account.analytic.account', string='Bộ phận thực hiện')
    management_id = fields.Many2one('account.analytic.account', string='Bộ phận quản lý')
    production_department = fields.Selection([('tu_san_xuat', 'Hàng tự sản xuất'),
                                              ('tp', 'Gia công TP'),
                                              ('npl', 'Gia công NPL')
                                              ], default='tu_san_xuat', string='Phân loại sản xuất')
    produced_from_date = fields.Date(string="Dự kiến sản xuất từ")
    to_date = fields.Date(string="Đến ngày")
    brand_id = fields.Many2one('res.brand', string="Nhãn hàng")
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('wait_confirm', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
    ], default='draft')
    status = fields.Selection([
        ('assigned', 'Chưa thực hiện'),
        ('in_approved', 'Đã nhập kho'),
        ('done', 'Hoàn thành'),
    ], default='assigned')

    relationship_forlife_production_id = fields.Many2one('forlife.production', string="Quan hệ Production")

    forlife_production_finished_product_ids = fields.One2many('production.history.line', 'forlife_production_id', string='Finished Products')


class ProductionHistoryLine(models.Model):
    _name = 'production.history.line'
    _description = 'Production History Line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'forlife_production_id'

    forlife_production_id = fields.Many2one('production.history', string='Mã lệnh sản xuất')
    forlife_production_name = fields.Char(string='Tên lệnh sản xuất')
    product_id = fields.Many2one('product.product', string='Mã sản phẩm')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị')
    produce_qty = fields.Float(string='Số lượng sản xuât')
    unit_price = fields.Float(string='Đơn giá')
    stock_qty = fields.Float(string='Số lượng nhập kho')
    remaining_qty = fields.Float(string='Số lượng còn lại')
    description = fields.Char(string='Mô tả')
    implementation_id = fields.Many2one('account.analytic.account', string='Bộ phận thực hiện')
    management_id = fields.Many2one('account.analytic.account', string='Bộ phận quản lý')
    production_department = fields.Selection([('tu_san_xuat', 'Hàng tự sản xuất'),
                                              ('tp', 'Gia công TP'),
                                              ('npl', 'Gia công NPL')
                                              ], string='Phân loại sản xuất')
    forlife_bom_material_ids = fields.One2many('material.history', 'forlife_production_id', string='Materials')
    forlife_bom_service_cost_ids = fields.One2many('service.cost.history', 'forlife_production_id', string='Service costs')
    forlife_bom_ingredients_ids = fields.One2many('ingredients.history', 'forlife_production_id', string='Ingredients')

    def action_open_bom_history(self):
        return {
            'name': ('BOM'),
            'view_mode': 'form',
            'view_id': self.env.ref('forlife_purchase.production_bom_history_form').id,
            'res_model': 'production.history.line',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }


class MaterialHistory(models.Model):
    _name = 'material.history'
    _description = 'Material History'

    forlife_production_id = fields.Many2one('production.history.line')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    description = fields.Char(string='Mô tả')
    quantity = fields.Integer()
    uom_id = fields.Many2one(related="product_id.uom_id", string='Đơn vị')
    production_uom_id = fields.Many2one('uom.uom', string='Đơn vị tính lệnh sản xuất')
    conversion_coefficient = fields.Float(string='Hệ số quy đổi')
    rated_level = fields.Float(string='Định mức')
    loss = fields.Float(string='Hao hụt %')
    total = fields.Float(string='Tổng nhu cầu')


class IngredientsHisory(models.Model):
    _name = 'ingredients.history'
    _description = 'Ingredients Hisory'

    forlife_production_id = fields.Many2one('production.history.line')
    product_id = fields.Many2one('product.product', string='Mã nguyên liệu')
    description = fields.Char(string='Tên nguyên liệu')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị tính lưu kho')
    production_uom_id = fields.Many2one('uom.uom', string='Đơn vị tính lưu kho')
    conversion_coefficient = fields.Float(string='Hệ số quy đổi')
    rated_level = fields.Float(string='Định mức')
    loss = fields.Float(string='Hao hụt %')
    total = fields.Float(string='Tổng nhu cầu')


class ServiceCostHistory(models.Model):
    _name = 'service.cost.history'
    _description = 'Service Cost History'

    forlife_production_id = fields.Many2one('production.history.line')
    product_id = fields.Many2one('product.product', string='Mã chi phí')
    rated_level = fields.Float(string='Định mức')