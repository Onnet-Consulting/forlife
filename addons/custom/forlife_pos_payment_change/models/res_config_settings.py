# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_payment_change_journal_id = fields.Many2one(
        'account.journal', string="Payment Change Journal", related='company_id.pos_payment_change_journal_id', \
        readonly=False)
