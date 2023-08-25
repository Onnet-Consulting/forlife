from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def name_get(self):
        result = []
        for location in self:
            if not location.type_other:
                name = f'[{location.code}] {location.complete_name}'
            else:
                name = location.complete_name
            result.append((location.id, name))
        return result
