# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.fields import Command


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_promotion = fields.Boolean(string='Is Promotion')

    @api.onchange('is_promotion')
    def onchange_is_promotion(self):
        for rec in self.search([('is_promotion', '=', True), ('id', '!=', self._origin.id)]):
            rec.write({'is_promotion': False})