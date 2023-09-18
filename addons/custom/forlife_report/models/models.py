# -*- coding:utf-8 -*-

from odoo import models, api, tools, _
from odoo.osv import expression
import ast


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('report_ctx'):
            model_permission = ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('model_permission_config') or '{}')
            if self._name in model_permission.keys():
                domain = [(model_permission.get(self._name), 'in', self.env.user.get_rule_report_config())]
                args = expression.AND([args, domain])
        return super()._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
