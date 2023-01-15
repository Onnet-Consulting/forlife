# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_payment_change_journal_id = fields.Many2one('account.journal', string='Payment Change Journal')
