# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
import re

CONTEXT_JOURNAL_ACTION = 'bravo_journal_data'
CONTEXT_UPDATE_JOURNAL = 'bravo_update_move'


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'bravo.model.insert.action']

    @api.model
    def sync_bravo_account_move_daily(self, **kwargs):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return False
        date = (kwargs.get('date') and datetime.strptime(kwargs.get('date'), '%d/%m/%Y')) or fields.Date.today()
        domain = [
            ('state', '=', 'posted'),
            ('date', '=', date),
        ]
        companies = self.env['res.company'].search([('code', '!=', False)])
        for company in companies:
            dm = domain + [('company_id', '=', company.id)]
            move_count = self.search_count(dm)
            if move_count > 0:
                self._action_sync_account_move(company, dm, date)

    @api.model
    def _action_sync_account_move(self, company, domain, date):
        moves = self.with_company(company).search(domain)
        for move in moves:
            insert_queries = move.bravo_get_insert_sql()
            if insert_queries:
                self.env[self._name].sudo().with_delay(
                    description=f'Bravo: sync account_move {move.name or move.id} [{date.strftime("%d/%m/%Y")}]', channel="root.Bravo").bravo_execute_query(insert_queries)
        return True

    @api.model
    def bravo_get_table(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        journal_update = kwargs.get(CONTEXT_UPDATE_JOURNAL)
        bravo_table = 'DEFAULT'
        if journal_data in (
                'purchase_asset_service',
                'purchase_product_cost_picking',
        ):
            bravo_table = 'B30AccDocPurchase'
        elif journal_data in (
                'purchase_asset_service_reversed',
                'purchase_product_cost_picking_reversed'):
            bravo_table = 'B30AccDocPurchaseReturn'
        elif journal_data in ('purchase_product_reserved', "purchase_product"):
            bravo_table = 'B30AccDocOther'
        elif journal_data == "purchase_bill_vendor_back":
            bravo_table = 'B30AccDocAtchDoc'
        elif journal_data == 'pos_cash_out':
            bravo_table = "B30AccDocCashPayment"
        elif journal_data == "pos_cash_in":
            bravo_table = "B30AccDocCashReceipt"
        elif journal_data == "journal_entry_payroll":
            bravo_table = "B30AccDocJournalEntry"
        elif journal_data == "order_exist_bkav":
            bravo_table = "B30AccDocExportSales"
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
            initial_records = self.env['account.move']
            for move in self.filtered(lambda m: m.purchase_type in ['service', 'asset']):
                if move.invoice_type == "increase":
                    initial_records |= move
                if not move.reversed_entry_id and move.invoice_line_ids.mapped('purchase_order_id'):
                    initial_records |= move
            return initial_records

        if journal_data == 'purchase_asset_service_reversed':
            initial_records = self.env['account.move']
            for move in self.filtered(lambda m: m.purchase_type in ['service', 'asset']):
                if move.invoice_type == "decrease":
                    initial_records |= move
                if move.reversed_entry_id and move.reversed_entry_id.invoice_line_ids.mapped('purchase_order_id'):
                    initial_records |= move
            return initial_records

        if journal_data == 'purchase_product':
            initial_records = self.env['account.move']
            for move in self.filtered(lambda m: m.purchase_type == 'product'):
                if move.invoice_type == "increase":
                    initial_records |= move
                if not move.reversed_entry_id and move.invoice_line_ids.mapped('purchase_order_id').filtered(
                        lambda o: not o.is_return):
                    initial_records |= move
                if move.reversed_entry_id and move.reversed_entry_id.invoice_line_ids.mapped(
                        'purchase_order_id').filtered(lambda o: o.is_return):
                    initial_records |= move
            return initial_records

        if journal_data == 'purchase_product_reserved':
            initial_records = self.env['account.move']
            for move in self.filtered(lambda m: m.purchase_type == 'product'):
                if move.invoice_type == "decrease":
                    initial_records |= move
                if not move.reversed_entry_id and move.invoice_line_ids.mapped('purchase_order_id').filtered(
                        lambda o: o.is_return):
                    initial_records |= move
                if move.reversed_entry_id and move.reversed_entry_id.invoice_line_ids.mapped(
                        'purchase_order_id').filtered(lambda o: not o.is_return):
                    initial_records |= move
            return initial_records

        if journal_data == "purchase_bill_vendor_back":
            return self.filtered(
                lambda m: len(m.line_ids.mapped('purchase_line_id')) > 0 and len(m.vendor_back_ids) > 0)
        # FIXME: switch ^CD -> ^972
        if journal_data == "purchase_product_cost_picking":
            initial_records = self.env['account.move']
            for move in self:
                # if not re.match('^972', move.name)
                if not re.match('^CD', move.name):
                    continue
                stock_picking = self.env['stock.picking'].sudo().search([('name', '=', move.ref)], limit=1)
                if not stock_picking or stock_picking.x_is_check_return:
                    continue
                initial_records |= move
            return initial_records

        # FIXME: switch ^CD -> ^972
        if journal_data == "purchase_product_cost_picking_reversed":
            initial_records = self.env['account.move']
            for move in self:
                # if not re.match('^972', move.name)
                if not re.match('^CD', move.name):
                    continue
                stock_picking = self.env['stock.picking'].sudo().search([('name', '=', move.ref)], limit=1)
                if not stock_picking or not stock_picking.x_is_check_return:
                    continue
                initial_records |= move
            return initial_records

        if journal_data == "pos_cash_out":
            return self.filtered(lambda m: m.journal_id.code == 'CA02'
                                           and bool(
                m.line_ids.filtered(lambda l: re.match("^111", l.account_id.code) and l.credit > 0)))
        if journal_data == "pos_cash_in":
            return self.filtered(lambda m: m.journal_id.code == 'CA02'
                                           and bool(
                m.line_ids.filtered(lambda l: re.match("^111", l.account_id.code) and l.debit > 0)))
        if journal_data == "journal_entry_payroll":
            return self.filtered(lambda am: am.journal_id.code == '971')
        if journal_data == "order_exist_bkav":
            return self.filtered(lambda am: am.exists_bkav and am.stock_move_id and am.stock_move_id.picking_id and
                                            ((am.stock_move_id.picking_id.sale_id and not am.stock_move_id.picking_id.sale_id.x_is_return) or
                                             am.stock_move_id.picking_id.pos_order_id))
        return self

    def bravo_get_insert_values(self, **kwargs):
        journal_data = kwargs.get(CONTEXT_JOURNAL_ACTION)
        update_move_data = kwargs.get(CONTEXT_UPDATE_JOURNAL)
        if journal_data == 'purchase_asset_service':
            return self.bravo_get_purchase_asset_service_values()
        if journal_data == 'purchase_asset_service_reversed':
            return self.bravo_get_purchase_asset_service_values(is_reversed=True)
        if journal_data == 'purchase_product':
            return self.bravo_get_purchase_product_values()
        if journal_data == 'purchase_product_reserved':
            return self.bravo_get_purchase_product_values(is_reversed=True)
        if journal_data == 'purchase_bill_vendor_back':
            return self.bravo_get_purchase_bill_vendor_back_values()
        if journal_data == 'purchase_product_cost_picking':
            return self.bravo_get_picking_purchase_costing_values()
        if journal_data == 'purchase_product_cost_picking_reversed':
            return self.bravo_get_picking_purchase_costing_values(is_reversed=True)
        if journal_data == "pos_cash_out":
            return self.bravo_get_cash_out_move_values()
        if journal_data == "pos_cash_in":
            return self.bravo_get_cash_in_move_values()
        if journal_data == "journal_entry_payroll":
            return self.bravo_get_journal_entry_payroll_values()
        if journal_data == "order_exist_bkav":
            return self.bravo_get_order_exist_bkav_values()
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

        # Purchase Asset + Service reversed (return)
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_asset_service_reversed'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_asset_service_reversed_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_asset_service_reversed_queries:
            queries.extend(purchase_asset_service_reversed_queries)

        # Purchase Product
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_product'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_product_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_product_queries:
            queries.extend(purchase_product_queries)

        # Purchase Product reversed (return)
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_product_reserved'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_product_reversed_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_product_reversed_queries:
            queries.extend(purchase_product_reversed_queries)

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

        # Purchase Product Cost From Picking reversed (return)
        current_context = {CONTEXT_JOURNAL_ACTION: 'purchase_product_cost_picking_reversed'}
        records = self.bravo_filter_record_by_context(**current_context)
        purchase_product_cost_picking_reversed_queries = records.bravo_get_insert_sql(**current_context)
        if purchase_product_cost_picking_reversed_queries:
            queries.extend(purchase_product_cost_picking_reversed_queries)

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

        # Journal entry payroll
        current_context = {CONTEXT_JOURNAL_ACTION: 'journal_entry_payroll'}
        records = self.bravo_filter_record_by_context(**current_context)
        journal_entry_payroll_queries = records.bravo_get_insert_sql(**current_context)
        if journal_entry_payroll_queries:
            queries.extend(journal_entry_payroll_queries)

        # Order exist_bkav
        current_context = {CONTEXT_JOURNAL_ACTION: 'order_exist_bkav'}
        records = self.bravo_filter_record_by_context(**current_context)
        order_exist_bkav_queries = records.bravo_get_insert_sql(**current_context)
        if order_exist_bkav_queries:
            queries.extend(order_exist_bkav_queries)

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
                "OldValue": re.sub('<.*?>', '', record.invoice_description or ''),
                "NewValue": re.sub('<.*?>', '', kwargs.get('invoice_description') or ''),
            }
            values.append(value)
        return columns, values

    def write(self, vals):
        records = self.filtered(lambda r: r.state == 'posted' and r.date != fields.Date.today())
        if 'invoice_description' not in vals or not bool(records):
            return super().write(vals)
        vals.update({CONTEXT_UPDATE_JOURNAL: True})
        insert_queries = records.bravo_get_insert_sql(**vals)
        if self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up") and insert_queries:
            self.env[self._name].sudo().with_delay(channel="root.Bravo").bravo_execute_query(insert_queries)
        vals.pop(CONTEXT_UPDATE_JOURNAL, None)
        return super().write(vals)
