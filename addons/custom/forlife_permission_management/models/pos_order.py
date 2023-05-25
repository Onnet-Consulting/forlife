# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    store_id = fields.Many2one('store', string='Store', related='config_id.store_id', related_sudo=True)