from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class StockLocationMapping(models.Model):
    _name = 'stock.location.mapping'
    _description = 'Cấu hình vị trí tương ứng các công ty'
    _rec_names_search = ['location_id', 'location_map_id']

    company_location_id = fields.Many2one('res.company', string='Công ty xuất bán')
    location_id = fields.Many2one('stock.location', 'Địa điểm xuất bán', domain="[('company_id', '=', company_location_id)]")
    company_location_map_id = fields.Many2one('res.company', string='Công ty nhập mua')
    location_map_id = fields.Many2one('stock.location', 'Địa điểm nhập mua', compute='_compute_location_mapping', store=True)
    inter_company = fields.Boolean(string='Địa điểm ảo liên công ty', default=False)

    def name_get(self):
        return [(rec.id, '%s' % rec.location_id.name_get()[0][1]) for rec in self]

    @api.constrains('location_id')
    def constrain_location_id(self):
        for r in self:
            location_exits = self.env['stock.location.mapping'].sudo().search([('location_id','=',r.location_id.id),('id','!=', r.id)])
            if location_exits:
                raise ValidationError(_('Đã tồn tại liên kết này !'))

    @api.depends('company_location_map_id')
    def _compute_location_mapping(self):
        for rec in self:
            if rec.location_id.code:
                location_map_id = self.env['stock.location'].sudo().search([('code','=',rec.location_id.code),('company_id','=', rec.company_location_map_id.id)], limit=1)
                if location_map_id:
                    rec.location_map_id = location_map_id.id
                else:
                    rec.location_map_id = False
            else:
                rec.location_map_id = False
