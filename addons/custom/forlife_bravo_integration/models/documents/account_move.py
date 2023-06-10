# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

CONTEXT_JOURNAL_ACTION = 'bravo_journal_data'


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
        bravo_table = 'DEFAULT'
        if journal_data == 'purchase_asset_service':
            bravo_table = 'B30AccDocPurchase'
        elif journal_data == "purchase_product":
            bravo_table = 'B30AccDocOther'
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
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        if journal_data == 'purchase_asset_service':
            return self.bravo_get_purchase_asset_service_values()
        if journal_data == 'purchase_product':
            return self.bravo_get_purchase_product_values()
        if journal_data == 'purchase_bill_vendor_back':
            return self.bravo_get_purchase_bill_vendor_back_values()
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

        return queries

    def bravo_get_insert_sql(self, **kwargs):
        if kwargs.get(CONTEXT_JOURNAL_ACTION):
            return super().bravo_get_insert_sql(**kwargs)
        return self.bravo_get_insert_sql_by_journal_action()
