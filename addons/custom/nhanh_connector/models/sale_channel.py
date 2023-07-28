# -*- coding: utf-8 -*-

from odoo import _, models, fields, api

class Salechannel(models.Model):
    _name = 'sale.channel'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name')
    nhanh_id = fields.Char(string='Id Nhanh.vn')
    is_tmdt = fields.Boolean(string='Sàn TMĐT', default=False)
    partner_id = fields.Many2one('res.partner', 'Khách Hàng')