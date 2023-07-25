from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_source_record = fields.Boolean(
        string="Đơn hàng từ nhanh", 
        related='sale_id.source_record'
    )

    nhanh_id = fields.Char(string='Id Nhanh.vn', related='sale_id.nhanh_id')

