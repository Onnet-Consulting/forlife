from odoo import fields, api, models


class ForlifeProduction(models.Model):
    _inherit = 'forlife.production'

    material_import_ids = fields.One2many('production.material.import', 'production_id')


class ProductionMaterialImport(models.Model):
    _name = 'production.material.import'
    _description = "Production material import"

    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Mã vật tư')
    size = fields.Char(string='Size')
    color = fields.Char(string='Màu')
    uom_id = fields.Many2one('uom.uom', string='ĐVT Lưu kho')
    production_uom_id = fields.Many2one('uom.uom', string='ĐVT Lệnh sản xuất')
    conversion_coefficient = fields.Float(string='HSQĐ')
    rated_level = fields.Float(string='Định mức')
    loss = fields.Float(string='Hao hụt')
    qty = fields.Float(string='Số lượng xuất')
    total = fields.Float(string='Tổng nhu cầu')
