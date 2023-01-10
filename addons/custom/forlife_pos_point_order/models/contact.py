from odoo import api, fields, models


class Contact(models.Model):
    _inherit = 'res.partner'

    is_purchased = fields.Boolean('Is Purchased', compute='_compute_is_purchased')

    def _compute_is_purchased(self):
        partner_exits = self.env['pos.order'].sudo().search([('partner_id','=', self.id)], limit=1)
        for rec in self:
            if partner_exits:
                rec.is_purchased = True
            else:
                rec.is_purchased = False


