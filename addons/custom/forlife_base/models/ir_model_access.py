# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    menu_ids = fields.Many2many('ir.ui.menu', string='Menu', compute='_get_menu_ids', store=True, compute_sudo=True)

    @api.depends('model_access')
    def _get_access_count(self):
        for access in self:
            arr_menu = []
            if access.model_id:
                arr_menu = access.model_id.menu_ids.ids
            access.menu_ids = [(6, 0, arr_menu)]