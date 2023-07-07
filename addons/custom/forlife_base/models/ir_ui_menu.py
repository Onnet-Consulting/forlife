# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class IrUIMenu(models.Model):
    _inherit = 'ir.ui.menu'

    model_id = fields.Many2one('ir.model', string='Model', compute='_get_model_id', store=True, compute_sudo=True)

    @api.depends('action')
    def _get_model_id(self):
        for menu in self:
            if not menu.action or menu.action._name != 'ir.actions.act_window':
                menu.model_id = False
                continue
            model_name = menu.action.res_model
            menu.model_id = menu.model_id.search([('model', '=', model_name)], limit=1)