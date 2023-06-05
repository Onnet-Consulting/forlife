from odoo import fields, models, api, _


class Location(models.Model):
    _inherit = 'stock.location'

    stock_location_type_id = fields.Many2one('stock.location.type', string="Stock Location Type")
    code_location = fields.Char(string="Code Location", compute="compute_code_location", store=True)
    usage = fields.Selection(selection_add=[('import/export', 'Import Other/Export Other')],
                             ondelete={'import/export': 'set default'})

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

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['usage'] = 'inventory'
        return res

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu lý do'),
            'template': '/forlife_stock/static/src/xlsx/lý_do_nk_xk.xlsx?download=true'
        }]
