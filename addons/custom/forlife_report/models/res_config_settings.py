# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    model_permission_config = fields.Char(string='Đối tượng được phân quyền', config_parameter="model_permission_config", default='{}')
