# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

CONTEXT_PICKING_ACTION = 'bravo_picking_data'


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'bravo.model.insert.action']

    def _action_done(self):
        res = super()._action_done()
        done_pickings = self.filtered(lambda p: p.state == 'done')
        insert_queries = done_pickings.bravo_get_insert_sql()
        self.env[self._name].sudo().with_delay().bravo_execute_query(insert_queries)
        return res

    @api.model
    def bravo_get_table(self):
        picking_data = self.env.context.get(CONTEXT_PICKING_ACTION)
        bravo_table = 'DEFAULT'
        if picking_data == "picking_purchase":
            bravo_table = "B30AccDocPurchase"
        return bravo_table

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_filter_record_by_context(self, **kwargs):
        picking_data = kwargs.get(CONTEXT_PICKING_ACTION)
        if picking_data == 'picking_purchase':
            return self.filtered(lambda m: m.stock_move_id.purchase_line_id)
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_PICKING_ACTION)
        if journal_data == 'picking_purchase':
            return self.bravo_get_picking_purchase_values()
        return [], []

    def bravo_get_insert_sql_by_picking_action(self):
        queries = []

        # Picking Purchase
        current_context = {CONTEXT_PICKING_ACTION: 'picking_purchase'}
        records = self.bravo_filter_record_by_context(**current_context)
        picking_purchase_queries = records.bravo_get_insert_sql(**current_context)
        if picking_purchase_queries:
            queries.extend(picking_purchase_queries)

        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_PICKING_ACTION):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_insert_sql_by_picking_action()
