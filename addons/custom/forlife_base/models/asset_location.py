from odoo import api, fields, models


class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Asset Location'

    code = fields.Char('Code')
    name = fields.Char('Name')
    address = fields.Char("Address")
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        if self._context.get('show_code'):
            result = []
            for l in self:
                result.append((l.id, f"[{l.code}] {l.name}" if l.code else l.name))
            return result
        return super().name_get()
