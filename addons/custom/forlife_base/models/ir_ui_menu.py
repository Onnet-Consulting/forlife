# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class IrUIMenu(models.Model):
    _inherit = 'ir.ui.menu'

    model_id = fields.Many2one('ir.model', string='Model', compute='_get_model_id')

    @api.depends('action')
    def _get_model_id(self):
        for menu in self.filtered(lambda m: m.action):
            if menu.action._name != 'ir.actions.act_window':
                continue
            model_name = menu.action.res_model
            menu.model_id = menu.model_id.search([('model', '=', model_name)], limit=1)