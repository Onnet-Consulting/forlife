from odoo import api, fields, models

class Product(models.Model):
    _inherit = 'product.template'

    tolerance = fields.Float('Tolerance')
    tolerance_ids = fields.One2many('product.tolerance.line', 'product_id', string='Supplier Tolerance')
    sku_code = fields.Char('Mã SKU')
    default_code = fields.Char(string='Mã hiển thị')

    @api.onchange('detailed_type')
    def onchange_detailed_type(self):
        if self.detailed_type == 'asset':
            return {'domain': {'categ_id': [('asset_group', '=', True)]}}
        else:
            return {'domain': {'categ_id': [('asset_group', '=', False)]}}