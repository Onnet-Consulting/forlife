# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Store(models.Model):
    _inherit = 'store'

    is_post_bkav = fields.Boolean('Có phát hành hóa đơn bkav')
