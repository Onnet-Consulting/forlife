# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResGroup(models.Model):
    _inherit = 'res.groups'

    # model_ids = fields.Many2many('ir.model', string='Model', compute='_get_model_id', store=True, compute_sudo=True)
    access_count = fields.Integer(string='Access count', compute='_get_access_count', compute_sudo=True)

    @api.depends('model_access')
    def _get_access_count(self):
        for group in self:
            group.access_count = len(group.model_access)

    def model_smart_button(self):
        return {
            'name': 'Models',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.model.access',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.model_access.ids)],
            'context': {'group_by': 'menu_ids'},
        }
