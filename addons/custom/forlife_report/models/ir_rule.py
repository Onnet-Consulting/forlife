# -*- coding:utf-8 -*-

from odoo import models, fields, api
import ast


class IrRule(models.Model):
    _inherit = 'ir.rule'

    is_report_rule = fields.Boolean('Áp dụng cho BÁO CÁO', default=False)

    def _get_rules(self, model_name, mode='read'):
        results = super(IrRule, self)._get_rules(model_name, mode)
        report_ctx = self._context.get('report_ctx') or ''
        model_permission = ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('model_permission_config') or '{}')
        if report_ctx and ',' in report_ctx and model_name in model_permission.keys():
            return results.filtered(lambda r: r.is_report_rule)
        elif report_ctx and model_name in model_permission.keys():
            return self.env[self._name]
        return results.filtered(lambda r: not r.is_report_rule)

    @api.model
    def _eval_context(self):
        res = dict(super()._eval_context())
        if self._context.get('report_ctx'):
            res.update({'user': self.env.user.with_context(**self._context)})
        return res
