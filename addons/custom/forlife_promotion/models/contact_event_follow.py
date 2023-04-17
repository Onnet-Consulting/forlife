from odoo import api, fields, models

class ContactEventFollow(models.Model):
    _name = 'contact.event.follow'

    _description = 'Khách hàng hưởng sự kiện (Customize luồng import)'

    partner_id = fields.Many2one('res.partner', 'Khách hàng')
    event_id = fields.Many2one('event', 'Sự kiện')
    internal_code = fields.Char('Mã nội bộ', related='partner_id.internal_code')

    def name_get(self):
        return [(rec.id, '%s' % rec.partner_id.name) for rec in self]