# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_rule_report_config(self):
        report_ctx = (self._context.get('report_ctx') or '').split(',')
        self._cr.execute(f"""
            select array_agg(distinct tb6.name) as data
            from res_group_report_users_rel tb1
                     join res_group_report_field_rel tb2 on tb1.res_group_report_id = tb2.res_group_report_id
                     join res_field_report tb3 on tb3.id = tb2.res_field_report_id
                     join ir_model_fields tb4 on tb4.id = tb3.field_id
                     join res_field_report_value_rel tb5 on tb5.res_field_report_id = tb3.id
                     join res_field_value_report tb6 on tb6.id = tb5.res_field_value_report_id
                     join ir_model tb7 on tb3.report_id = tb7.id
            where tb1.res_users_id = {self._uid}
              and tb7.model = '{report_ctx[0]}'
              {f"and tb4.name = '{report_ctx[2]}'" if len(report_ctx) > 2 else ''}
              and tb4.relation = '{report_ctx[1]}'""")
        result = self._cr.fetchone()
        return result and result[0] or []
