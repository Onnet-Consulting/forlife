from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class StockLocationMapping(models.Model):
    _name = 'stock.location.mapping'
    _description = 'Cấu hình vị trí tương ứng các công ty'
    _rec_names_search = ['location_id', 'location_map_id']

    location_id = fields.Many2one('stock.location', 'Địa điểm (Công ty sản xuất)', domain=[('company_id.code', '=', '1300')])
    location_map_id = fields.Many2one('stock.location', 'Địa điểm tương ứng(Công ty bán lẻ)', compute='_compute_location_mapping', store=True)

    def name_get(self):
        return [(rec.id, '%s' % rec.location_id.name_get()[0][1]) for rec in self]

    @api.constrains('location_id')
    def constrain_location_id(self):
        for r in self:
            location_exits = self.env['stock.location.mapping'].sudo().search([('location_id','=',r.location_id.id),('id','!=', self.id)])
            if location_exits:
                raise ValidationError(_('Đã tồn tại liên kết này !'))

    @api.depends('location_id')
    def _compute_location_mapping(self):
        for rec in self:
            if rec.location_id.code:
                company = self.env['res.company'].search([('code','=','1400')])
                location_map_id = self.env['stock.location'].sudo().search([('code','=',rec.location_id.code),('company_id','=', company.id)], limit=1)
                if location_map_id:
                    rec.location_map_id = location_map_id.id
                else:
                    rec.location_map_id = False
            else:
                rec.location_map_id = False
