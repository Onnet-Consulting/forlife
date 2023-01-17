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

    def _pos_data_process(self, loaded_data):
        super(PosSession, self)._pos_data_process(loaded_data)
        loaded_data['assignable_employees'] = self._get_assignable_employees()

    def _get_assignable_employees(self):
        """Get assignable employees for PoS order line"""
        return self.env['hr.employee'].search_read([('id', 'in', self.config_id.store_id.employee_ids.ids)], ['name'])
