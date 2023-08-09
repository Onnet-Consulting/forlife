# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    is_synthetic = fields.Boolean(string='Synthetic', default=False, copy=False)

