# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    is_post_bkav_store = fields.Boolean(
        string='Có phát hành hóa đơn bkav', 
        related="pos_order_id.is_post_bkav_store"
    )

