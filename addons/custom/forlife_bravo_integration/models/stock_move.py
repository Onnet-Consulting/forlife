# -*- coding:utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta

CONTEXT_MOVE_ACTION = 'bravo_move_action'


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'bravo.model.insert.action']

    @api.model
    def sync_bravo_stock_move_daily(self, **kwargs):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return False
        date = (kwargs.get('date') and datetime.strptime(kwargs.get('date'), '%d/%m/%Y')) or fields.Datetime.now()
        begin_date = (date + timedelta(days=-1)).replace(hour=17, second=0, minute=0)
        end_date = date.replace(hour=17, second=0, minute=0)
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', begin_date),
            ('date', '<', end_date),
        ]
        companies = self.env['res.company'].search([('code', '!=', False)])
        for company in companies:
            dm = domain + [('company_id', '=', company.id)]
            picking_count = self.search_count(dm)
            if picking_count > 0:
                self._action_sync_stock_move(company, dm)

    @api.model
    def _action_sync_stock_move(self, company, domain):
        records = self.with_company(company).search(domain)
        for record in records:
            insert_queries = record.bravo_get_insert_sql()
            if insert_queries:
                self.env[self._name].sudo().with_delay(
                    description=f'Bravo: sync stock_move {record.name or record.id}', channel="root.Bravo").bravo_execute_query(insert_queries)
        return True

    @api.model
    def bravo_get_table(self):
        move_type = self.env.context.get(CONTEXT_MOVE_ACTION)
        bravo_table = 'DEFAULT'
        if move_type == 'purchase_picking':
            bravo_table = 'B30AccDocPurchase'
        elif move_type == 'sale_picking':
            bravo_table = 'B30AccDocSales'
        return bravo_table

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_get_purchase_picking_data(self):
        moves = self.filtered(lambda m: m.purchase_line_id)
        bravo_column_names = []
        moves_data = []
        for idx, move in enumerate(moves, start=1):
            picking = move.picking_id
            picking_partner = picking.partner_id
            account_move = move.account_move_ids and move.account_move_ids[0]
            bravo_data = {
                'CompanyCode': picking.company_id.code,
                'Stt': picking.id,
                'DocCode': 'NK' if picking_partner.group_id == self.env.ref(
                    'forlife_pos_app_member.partner_group_1') else 'NM',
                'DocNo': picking.name,
                'DocDate': move.date,
                'CustomerCode': picking_partner.ref,
                'CustomerName': picking_partner.name,
                'Address': picking_partner.contact_address_complete,
                'EmployeeCode': picking.user_id.employee_id.code,
                'BuiltinOrder': idx
            }
            bravo_data.update({
                'Quantity9': move.quantity_done,
                'DocNo_PO': picking.origin,
                'WarehouseCode': move.location_dest_id.warehouse_id.code,
                'RowId': move.id,
                'DebitAccount': None,
                'CreditAccount': None,
            })
            for acl in account_move.line_ids:
                if acl.debit > 0:
                    bravo_data.update({
                        'DebitAccount': acl.account_id.code
                    })
                if acl.credit > 0:
                    bravo_data.update({
                        'CreditAccount': acl.account_id.code
                    })

            moves_data.append(bravo_data)
            if bravo_column_names:
                continue
            bravo_column_names = list(bravo_data.keys())
        return bravo_column_names, moves_data

    def bravo_get_sale_picking_data(self):
        moves = self.filtered(lambda m: m.sale_line_id)
        bravo_column_names = []
        moves_data = []
        for idx, move in enumerate(moves, start=1):
            picking = move.picking_id
            picking_partner = picking.partner_id
            account_move = move.account_move_ids and move.account_move_ids[0]
            quantity_done = move.quantity_done
            product = move.product_id
            bravo_data = {
                "CompanyCode": picking.company_id.code,
                'Stt': picking.id,
                'IssueNo': picking.name,
                'DocDate': move.date,
                'CurrencyCode': account_move.currency_id.name,
                'CustomerCode': picking_partner.ref,
                'CustomerName': picking_partner.name,
                'Address': picking_partner.contact_address_complete,
                'TaxRegNo': picking_partner.vat,
                'EmployeeCode': picking.user_id.employee_id.code,
                'BuiltinOrder': idx,
                'DebitAccount': None,
                'CreditAccount2': None,
                'ItemCode': product.barcode,
                'ItemName': product.name,
                'UnitCode': move.product_uom.code,
                'Quantity9': quantity_done,
                'Quantity': quantity_done,
                'ConvertRate9': 1,
                'WarehouseCode': move.location_id.warehouse_id.code,
                'RowId': move.id
            }
            credit = 0
            for acl in account_move.line_ids:
                if acl.debit > 0:
                    bravo_data.update({
                        'DebitAccount': acl.account_id.code
                    })
                if acl.credit > 0:
                    credit = acl.credit
                    bravo_data.update({
                        'CreditAccount2': acl.account_id.code
                    })
            bravo_data.update({
                'OriginalUnitCost': credit / quantity_done if quantity_done else 0,
                'UnitCost': credit / quantity_done if quantity_done else 0,
                'OriginalAmount': credit,
                'Amount': credit,
            })

            moves_data.append(bravo_data)
            if bravo_column_names:
                continue
            bravo_column_names = list(bravo_data.keys())

        return bravo_column_names, moves_data

    def bravo_get_insert_values(self):
        move_type = self.env.context.get(CONTEXT_MOVE_ACTION)
        if move_type == 'purchase_picking':
            return self.bravo_get_purchase_picking_data()
        if move_type == 'sale_picking':
            return self.bravo_get_sale_picking_data()
        return [], []

    def bravo_get_insert_sql_by_move_action(self):
        queries = []
        purchase_picking_query = self.with_context(**{CONTEXT_MOVE_ACTION: 'purchase_picking'}).bravo_get_insert_sql()
        if purchase_picking_query:
            queries.extend(purchase_picking_query)
        sale_picking_query = self.with_context(**{CONTEXT_MOVE_ACTION: 'sale_picking'}).bravo_get_insert_sql()
        if sale_picking_query:
            queries.extend(sale_picking_query)
        return queries

    def bravo_get_insert_sql(self):
        if self.env.context.get(CONTEXT_MOVE_ACTION):
            return super().bravo_get_insert_sql()
        return self.bravo_get_insert_sql_by_move_action()
