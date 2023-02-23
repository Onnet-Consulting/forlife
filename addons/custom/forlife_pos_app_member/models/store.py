# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Store(models.Model):
    _inherit = 'store'

    contact_id = fields.Many2one('res.partner', string='Contact Store', required=True, domain=lambda self: [('group_id', 'in', self.env['res.partner.group'].search([('code', '=', '4000')]).ids)])
