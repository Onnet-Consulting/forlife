# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class ForlifeProduction(models.Model):
    _inherit = 'forlife.production'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('order_manager'):
            args = expression.AND([args, [('leader_id', '=', self._context.get('order_manager'))]])
        if self._context.get('machining'):
            args = expression.AND([args, [('machining_id', '=', self._context.get('machining'))]])
        if self._context.get('received'):
            self._cr.execute('''
            select array_agg(id) as ids
            from (select distinct forlife_production_id as id
                  from forlife_production_finished_product
                  group by forlife_production_id
                  having sum(coalesce(stock_qty, 0)) > 0) as xx
            ''')
            result = self._cr.dictfetchone() or {}
            args = expression.AND([args, [('id', 'in', result.get('ids') or [])]])
            args = expression.AND([args, [('state', '=', 'approved')]])
        return super()._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
