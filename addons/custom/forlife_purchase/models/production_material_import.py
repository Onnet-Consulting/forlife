from odoo import fields, api, models


class ForlifeProduction(models.Model):
    _inherit = 'forlife.production'

    material_import_ids = fields.One2many('production.material.import', 'production_id')
    expense_import_ids = fields.One2many('production.expense.import', 'production_id')


class ProductionMaterialImport(models.Model):
    _name = 'production.material.import'
    _description = "Production material import"

    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Mã vật tư')
    product_backup_id = fields.Many2one('product.product', string='Mã vật tư thay thế')
    size = fields.Char(string='Size')
    color = fields.Char(string='Màu')
    uom_id = fields.Many2one('uom.uom', string='ĐVT Lưu kho')
    production_uom_id = fields.Many2one('uom.uom', string='ĐVT Lệnh sản xuất')
    conversion_coefficient = fields.Float(string='HSQĐ')
    rated_level = fields.Float(string='Định mức')
    loss = fields.Float(string='Hao hụt')
    qty = fields.Float(string='Số lượng sản xuất')
    total = fields.Float(string='Tổng nhu cầu')


class ProductionExpenseImport(models.Model):
    _name = 'production.expense.import'
    _description = "Production expense import"

    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Chi phí')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    quantity = fields.Float(string='Số lượng')
    cost_norms = fields.Float(string='Định mức')
    total_cost_norms = fields.Float(string='Tổng định mức')
