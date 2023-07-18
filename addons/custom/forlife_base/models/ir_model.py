# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class IrModel(models.Model):
    _inherit = 'ir.model'

    menu_ids = fields.Many2many('ir.ui.menu', string='Menu', compute='_get_menu_ids', store=True, compute_sudo=True)

    def _get_menu_ids(self):
        for model_id in self:
            sql = f"""SELECT id FROM ir_ui_menu WHERE model_id = {model_id.id}"""
            self._cr.execute(sql)
            menu_ids = self._cr.fetchall()
            model_id.menu_ids = [(6, 0, [i[0] for i in menu_ids])]

