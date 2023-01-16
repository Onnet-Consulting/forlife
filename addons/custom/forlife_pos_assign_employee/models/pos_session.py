# -*- coding:utf-8 -*-

from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        models_to_load = super()._pos_ui_models_to_load()
        new_model = 'hr.employee'
        if new_model not in models_to_load:
            models_to_load.append(new_model)
        return models_to_load
