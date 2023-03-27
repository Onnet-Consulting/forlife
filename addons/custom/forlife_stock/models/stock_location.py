from odoo import fields, models, api, _


class Location(models.Model):
    _inherit = 'stock.location'

    stock_location_type_id = fields.Many2one('stock.location.type', string="Stock Location Type")
    code_location = fields.Char(string="Code Location", compute="compute_code_location", store=True)

    @api.depends('warehouse_id', 'stock_location_type_id')
    def compute_code_location(self):
        for item in self:
            if item.parent_path and item.warehouse_id and item.warehouse_id.whs_type and item.stock_location_type_id and item.stock_location_type_id.code:
                if not item.code_location:
                    number_location = self.env['ir.sequence'].next_by_code('forlife.stock.number.location') or '0'
                    item.code_location = item.warehouse_id.whs_type.code + number_location + '/' + str(
                        item.stock_location_type_id.code)
            else:
                item.code_location = False