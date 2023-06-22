# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

CONTEXT_PICKING_ACTION = 'bravo_picking_data'
PICKING_PURCHASE_VALUE = 'picking_purchase'
PICKING_OTHER_IMPORT_VALUE = 'picking_other_import'
PICKING_OTHER_EXPORT_VALUE = 'picking_other_export'
PICKING_PURCHASE_RETURN_VALUE = 'picking_purchase_return'
CONTEXT_PICKING_UPDATE = 'bravo_picking_update'
CONTEXT_CANCEL_OTHER_PICKING = 'bravo_cancel_other_picking'


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
        picking_update = kwargs.get(CONTEXT_PICKING_UPDATE)
        cancel_other_picking = kwargs.get(CONTEXT_CANCEL_OTHER_PICKING)
        bravo_table = 'DEFAULT'
        if picking_data == PICKING_PURCHASE_VALUE:
            bravo_table = "B30AccDocPurchase"
        elif picking_data == PICKING_OTHER_IMPORT_VALUE:
            bravo_table = "B30AccDocItemReceipt"
        elif picking_data == PICKING_OTHER_EXPORT_VALUE:
            bravo_table = "B30AccDocItemIssue"
        elif picking_data == PICKING_PURCHASE_RETURN_VALUE:
            bravo_table = "B30AccDocPurchaseReturn"
        elif picking_update:
            bravo_table = "B30UpdateData"
        elif cancel_other_picking:
            bravo_table = "B30UpdateData2"
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
                lambda p: p.move_ids.mapped('account_move_ids') and p.move_ids.mapped('purchase_line_id')
                          and not p.x_is_check_return and not p.is_return_po)
        if picking_data == PICKING_OTHER_IMPORT_VALUE:
            return self.filtered(lambda m: m.move_ids.mapped('account_move_ids') and m.other_import)
        if picking_data == PICKING_OTHER_EXPORT_VALUE:
            return self.filtered(lambda m: m.move_ids.mapped('account_move_ids') and m.other_export)
        if picking_data == PICKING_PURCHASE_RETURN_VALUE:
            return self.filtered(
                lambda p: p.move_ids.mapped('account_move_ids') and p.move_ids.mapped('purchase_line_id')
                          and (p.x_is_check_return or p.is_return_po))
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_PICKING_ACTION)
        picking_update = kwargs.get(CONTEXT_PICKING_UPDATE)
        cancel_other_picking = kwargs.get(CONTEXT_CANCEL_OTHER_PICKING)
        if journal_data == PICKING_PURCHASE_VALUE:
            return self.bravo_get_picking_purchase_values()
        if journal_data == PICKING_OTHER_IMPORT_VALUE:
            return self.bravo_get_picking_other_import_values()
        if journal_data == PICKING_OTHER_EXPORT_VALUE:
            return self.bravo_get_picking_other_export_values()
        if journal_data == PICKING_PURCHASE_RETURN_VALUE:
            return self.bravo_get_return_picking_purchase_values()
        if picking_update:
            return self.bravo_get_update_picking_values(**kwargs)
        if cancel_other_picking:
            return self.bravo_get_cancel_other_picking_values()
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

        # Picking Purchase return
        current_context = {CONTEXT_PICKING_ACTION: PICKING_PURCHASE_RETURN_VALUE}
        records = self.bravo_filter_record_by_context(**current_context)
        picking_purchase_return_queries = records.bravo_get_insert_sql(**current_context)
        if picking_purchase_return_queries:
            queries.extend(picking_purchase_return_queries)

        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_PICKING_ACTION) or kwargs.get(CONTEXT_PICKING_UPDATE)\
                or kwargs.get(CONTEXT_CANCEL_OTHER_PICKING):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_insert_sql_by_picking_action()

    # -------------------- UPDATE --------------------------

    @api.model
    def bravo_get_update_picking_columns(self):
        return [
            "CompanyCode", "UpdateType", "DocNo", "DocDate",
            "Stt", "RowId", "ColumnName", "OldValue", "NewValue",
        ]

    def bravo_get_update_picking_values(self, **kwargs):
        columns = self.bravo_get_update_picking_columns()
        values = []
        for record in self:
            value = {
                "CompanyCode": record.company_id.code or None,
                "UpdateType": "1",
                "DocNo": record.name or None,
                "DocDate": record.date_done or None,
                "Stt": record.id,
                "RowId": record.id,
                "ColumnName": "Description",
                "OldValue": record.note or None,
                "NewValue": kwargs.get('note') or None,
            }
            values.append(value)
        return columns, values

    def write(self, vals):
        records = self.filtered(lambda r: r.state == 'done')
        if 'note' not in vals or not bool(records):
            return super().write(vals)
        vals.update({CONTEXT_PICKING_UPDATE: True})
        insert_queries = records.bravo_get_insert_sql(**vals)
        if insert_queries:
            self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(insert_queries)
        vals.pop(CONTEXT_PICKING_UPDATE, None)
        return super().write(vals)

    # ======================= cancel other export, import picking =============================
    @api.model
    def bravo_get_cancel_other_picking_columns(self):
        return [
            "CompanyCode", "DocCode", "DocNo", "DocDate", "Stt"
        ]

    def bravo_get_cancel_other_picking_values(self):
        columns = self.bravo_get_cancel_other_picking_columns()
        values = []
        for record in self:
            value = {
                "CompanyCode": record.company_id.code or None,
                "DocCode": "PN" if record.other_import else "PX",
                "DocNo": record.name or None,
                "DocDate": record.date_done or None,
                "Stt": record.name or None,
            }
            values.append(value)
        return columns, values

    def action_cancel(self):
        records = self.filtered(lambda r: r.state == 'done')
        res = super().action_cancel()
        records = records.filtered(lambda r: r.state == 'cancel')
        if records:
            queries = records.bravo_get_insert_sql(**{CONTEXT_CANCEL_OTHER_PICKING: True})
            self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(queries)
        return res
