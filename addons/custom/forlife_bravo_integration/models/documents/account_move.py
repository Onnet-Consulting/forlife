# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import re

CONTEXT_JOURNAL_ACTION = 'bravo_journal_data'
CONTEXT_UPDATE_JOURNAL = 'bravo_update_move'


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'bravo.model.insert.action']

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        posted_moves = self.filtered(lambda m: m.state == 'posted')
        insert_queries = posted_moves.bravo_get_insert_sql()
        self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(insert_queries)
        return res

    @api.model
    def bravo_get_table(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        journal_update = kwargs.get(CONTEXT_UPDATE_JOURNAL)
        bravo_table = 'DEFAULT'
        if journal_data == 'purchase_asset_service':
            bravo_table = 'B30AccDocPurchase'
        elif journal_data == "purchase_product":
            bravo_table = 'B30AccDocOther'
        elif journal_data == "purchase_bill_vendor_back":
            bravo_table = 'B30AccDocAtchDoc'
        elif journal_data == "purchase_product_cost_picking":
            bravo_table = "B30AccDocPurchase"
        elif journal_data == 'pos_cash_out':
            bravo_table = "B30AccDocCashPayment"
        elif journal_data == "pos_cash_in":
            bravo_table = "B30AccDocCashReceipt"
        elif journal_update:
            bravo_table = "B30UpdateData"
        return bravo_table

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_filter_record_by_context(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        if journal_data == 'purchase_asset_service':
            return self.filtered(lambda m: m.invoice_line_ids.mapped('purchase_order_id').
                                 filtered(lambda order: order.purchase_type in ['service', 'asset']))
        if journal_data == 'purchase_product':
            return self.filtered(lambda m: m.invoice_line_ids.mapped('purchase_order_id').
                                 filtered(lambda order: order.purchase_type == 'product'))
        if journal_data == "purchase_bill_vendor_back":
            return self.filtered(
                lambda m: len(m.line_ids.mapped('purchase_line_id')) > 0 and len(m.vendor_back_ids) > 0)
        # FIXME: switch ^CD -> ^972
        if journal_data == "purchase_product_cost_picking":
            return self.filtered(
                lambda m: bool(self.env['stock.picking'].sudo().search_count([('name', '=', m.ref)], limit=1))
                          and
                          re.match('^CD', m.name)
                # re.match('^972', m.name)
            )
        if journal_data == "pos_cash_out":
            return self.filtered(lambda m: m.journal_id.code == 'CA02'
                                           and bool(
                m.line_ids.filtered(lambda l: re.match("^111", l.account_id.code) and l.credit > 0)))
        if journal_data == "pos_cash_in":
            return self.filtered(lambda m: m.journal_id.code == 'CA02'
                                           and bool(
                m.line_ids.filtered(lambda l: re.match("^111", l.account_id.code) and l.debit > 0)))
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        update_move_data = kwargs.get(CONTEXT_UPDATE_JOURNAL)
        if journal_data == 'purchase_asset_service':
            return self.bravo_get_purchase_asset_service_values()
        if journal_data == 'purchase_product':
            return self.bravo_get_purchase_product_values()
        if journal_data == 'purchase_bill_vendor_back':
            return self.bravo_get_purchase_bill_vendor_back_values()
        if journal_data == 'purchase_product_cost_picking':
            return self.bravo_get_picking_purchase_costing_values()
        if journal_data == "pos_cash_out":
            return self.bravo_get_cash_out_move_values()
        if journal_data == "pos_cash_in":
            return self.bravo_get_cash_in_move_values()
        if update_move_data:
            return self.bravo_get_update_move_values(**kwargs)
        return [], []

    def bravo_get_insert_sql_by_journal_action(self):
        queries = []
        # Purchase Asset + Service
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_asset_service'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_asset_service_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_asset_service_queries:
            queries.extend(purchase_asset_service_queries)

        # Purchase Product
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_product'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_product_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_product_queries:
            queries.extend(purchase_product_queries)

        # Vendor Back in Purchase Bill
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_bill_vendor_back'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_bill_vendor_back_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_bill_vendor_back_queries:
            queries.extend(purchase_bill_vendor_back_queries)

        # Purchase Product Cost From Picking
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_product_cost_picking'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_product_cost_picking_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_product_cost_picking_queries:
            queries.extend(purchase_product_cost_picking_queries)

        # POS cash out
        current_context = {CONTEXT_JOURNAL_ACTION: 'pos_cash_out'}
        records = self.bravo_filter_record_by_context(**current_context)
        pos_cash_out_queries = records.bravo_get_insert_sql(**current_context)
        if pos_cash_out_queries:
            queries.extend(pos_cash_out_queries)

        # POS cash in
        current_context = {CONTEXT_JOURNAL_ACTION: 'pos_cash_in'}
        records = self.bravo_filter_record_by_context(**current_context)
        pos_cash_in_queries = records.bravo_get_insert_sql(**current_context)
        if pos_cash_in_queries:
            queries.extend(pos_cash_in_queries)

        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_JOURNAL_ACTION) or kwargs.get(CONTEXT_UPDATE_JOURNAL):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_insert_sql_by_journal_action()

    # -------------------- UPDATE --------------------------

    @api.model
    def bravo_get_update_move_columns(self):
        return [
            "CompanyCode", "UpdateType", "DocNo", "DocDate",
            "Stt", "RowId", "ColumnName", "OldValue", "NewValue",
        ]

    def bravo_get_update_move_values(self, **kwargs):
        columns = self.bravo_get_update_move_columns()
        values = []
        for record in self:
            value = {
                "CompanyCode": record.company_id.code,
                "UpdateType": "1",
                "DocNo": record.name,
                "DocDate": record.date,
                "Stt": record.id,
                "RowId": record.id,
                "ColumnName": "Description",
                "OldValue": record.invoice_description,
                "NewValue": kwargs.get('invoice_description'),
            }
            values.append(value)
        return columns, values

    def write(self, vals):
        records = self.filtered(lambda r: r.state == 'posted')
        if 'invoice_description' not in vals or not bool(records):
            return super().write(vals)
        vals.update({CONTEXT_UPDATE_JOURNAL: True})
        insert_queries = records.bravo_get_insert_sql(**vals)
        if insert_queries:
            self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(insert_queries)
        vals.pop(CONTEXT_UPDATE_JOURNAL, None)
        return super().write(vals)
