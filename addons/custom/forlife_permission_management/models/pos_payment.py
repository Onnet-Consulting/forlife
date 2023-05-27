# -*- coding:utf-8 -*-

from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    store_id = fields.Many2one('store', string='Store', related='session_id.store_id', related_sudo=True)