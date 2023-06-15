# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

CONTEXT_PICKING_ACTION = 'bravo_picking_data'
PICKING_PURCHASE_VALUE = 'picking_purchase'
PICKING_OTHER_IMPORT_VALUE = 'picking_other_import'
PICKING_OTHER_EXPORT_VALUE = 'picking_other_export'


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'bravo.model.insert.action']

    def _action_done(self):
        res = super()._action_done()
        done_pickings = self.filtered(lambda p: p.state == 'done')
        insert_queries = done_pickings.bravo_get_insert_sql()
        self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(insert_queries)
        return res

    @api.model
    def bravo_get_table(self, **kwargs):
        picking_data = kwargs.get(CONTEXT_PICKING_ACTION)
        bravo_table = 'DEFAULT'
        if picking_data == PICKING_PURCHASE_VALUE:
            bravo_table = "B30AccDocPurchase"
        elif picking_data == PICKING_OTHER_IMPORT_VALUE:
            bravo_table = "B30AccDocItemReceipt"
        elif picking_data == PICKING_OTHER_EXPORT_VALUE:
            bravo_table = "B30AccDocItemIssue"
        return bravo_table

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_filter_record_by_context(self, **kwargs):
        picking_data = kwargs.get(CONTEXT_PICKING_ACTION)
        if picking_data == PICKING_PURCHASE_VALUE:
            return self.filtered(
                lambda m: m.move_ids.mapped('account_move_ids') and m.move_ids.mapped('purchase_line_id'))
        if picking_data == PICKING_OTHER_IMPORT_VALUE:
            return self.filtered(lambda m: m.move_ids.mapped('account_move_ids') and m.other_import)
        if picking_data == PICKING_OTHER_EXPORT_VALUE:
            return self.filtered(lambda m: m.move_ids.mapped('account_move_ids') and m.other_export)
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_PICKING_ACTION)
        if journal_data == PICKING_PURCHASE_VALUE:
            return self.bravo_get_picking_purchase_values()
        if journal_data == PICKING_OTHER_IMPORT_VALUE:
            return self.bravo_get_picking_other_import_values()
        if journal_data == PICKING_OTHER_EXPORT_VALUE:
            return self.bravo_get_picking_other_export_values()
        return [], []

    def bravo_get_insert_sql_by_picking_action(self):
        queries = []

        # Picking Purchase
        current_context = {CONTEXT_PICKING_ACTION: PICKING_PURCHASE_VALUE}
        records = self.bravo_filter_record_by_context(**current_context)
        picking_purchase_queries = records.bravo_get_insert_sql(**current_context)
        if picking_purchase_queries:
            queries.extend(picking_purchase_queries)

        # Picking other import
        current_context = {CONTEXT_PICKING_ACTION: PICKING_OTHER_IMPORT_VALUE}
        records = self.bravo_filter_record_by_context(**current_context)
        picking_other_import_queries = records.bravo_get_insert_sql(**current_context)
        if picking_other_import_queries:
            queries.extend(picking_other_import_queries)

        # Picking other export
        current_context = {CONTEXT_PICKING_ACTION: PICKING_OTHER_EXPORT_VALUE}
        records = self.bravo_filter_record_by_context(**current_context)
        picking_other_export_queries = records.bravo_get_insert_sql(**current_context)
        if picking_other_export_queries:
            queries.extend(picking_other_export_queries)

        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_PICKING_ACTION):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_insert_sql_by_picking_action()
