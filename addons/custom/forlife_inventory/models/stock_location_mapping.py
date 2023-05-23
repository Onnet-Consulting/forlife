from odoo import api, fields, models,_

class StockLocationMapping(models.Model):
    _name = 'stock.location.mapping'
    _description = 'Cấu hình vị trí tương ứng các công ty'
    _rec_names_search = ['location_id', 'location_child_id']

    location_id = fields.Many2one('stock.location', 'Địa điểm')
    location_child_id = fields.Many2one('stock.location', 'Địa điểm tương ứng', compute='_compute_location_mapping', store=True)

    def name_get(self):
        return [(rec.id, '%s' % rec.location_id.name_get()[0][1]) for rec in self]

    @api.depends('location_id')
    def _compute_location_mapping(self):
        for rec in self:
            if rec.location_id:
                rec.location_child_id = self.env['stock.location'].sudo().search([('code','=',rec.location_id.code),('company_id','!=', rec.location_id.company_id.id)], limit=1)
            else:
                rec.location_child_id = False
