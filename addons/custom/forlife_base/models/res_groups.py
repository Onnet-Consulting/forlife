# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResGroup(models.Model):
    _inherit = 'res.groups'

    model_ids = fields.Many2many('ir.model', string='Model', compute='_get_model_id', store=True, compute_sudo=True)
    model_count = fields.Integer(string='Model count', compute='_get_model_id', compute_sudo=True)

    @api.depends('model_access')
    def _get_model_id(self):
        for group in self:
            arr_model = []
            if group.model_access:
                arr_model = group.model_access.mapped('model_id.id')
            group.model_ids = [(6, 0, arr_model)]
            group.model_count = len(arr_model)

    def model_smart_button(self):
        return {
            'name': 'Models',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.model',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.model_ids.ids)],
            'context': {'group_by': 'menu_ids'},
        }
