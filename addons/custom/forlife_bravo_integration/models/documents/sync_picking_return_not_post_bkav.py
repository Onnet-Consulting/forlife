# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class SyncPickingReturnNotPostBkav(models.AbstractModel):
    _name = 'picking.return.not.post.bkav'
    _inherit = 'bravo.model.insert.action'
    _bravo_table = 'B30AccDocSalesReturn'

    @api.model
    def sync_picking_return_not_post_bkav(self, picking_sale, picking_pos):
        values = []
        sale_values = {}
        pos_values = {}

        for picking in picking_sale:
            date_done = (picking.date_done + timedelta(hours=7)).strftime('%Y-%m-%d')
            for stock_move in picking.move_ids:
                key = f"TLO{stock_move.location_dest_id.warehouse_id.code}{date_done[2:4]}_{date_done}"
                value = sale_values.get(key) or stock_move
                value |= stock_move
                sale_values.update({key: value})

        for picking in picking_pos:
            date_done = (picking.date_done + timedelta(hours=7)).strftime('%Y-%m-%d')
            for stock_move in picking.move_ids:
                key = f"TLP{stock_move.location_dest_id.warehouse_id.code}{date_done[2:4]}_{date_done}"
                value = pos_values.get(key) or stock_move
                value |= stock_move
                pos_values.update({key: value})

        for key, value in sale_values.items():
            split_key = key.split('_')
            sequence_key = split_key[0]
            sequence_stt = self.env['ir.sequence'].search([('code', '=', sequence_key)], limit=1)
            if not sequence_stt:
                vals = {
                    'name': 'Gom phiếu trả hàng SO nhanh: ' + sequence_key,
                    'code': sequence_key,
                    'company_id': None,
                    'prefix': sequence_key,
                    'padding': 7,
                    'number_increment': 1,
                    'number_next_actual': 1
                }
                sequence_stt = self.env['ir.sequence'].create(vals)
            product_ids = value.product_id
            while product_ids:
                _product_ids = product_ids[:1000]
                stt_key = sequence_stt._next()
                for idx, product in enumerate(_product_ids, start=1):
                    move_free_good = value.filtered(lambda f: f.product_id == product and f.free_good)
                    move_not_free_good = value.filtered(lambda f: f.product_id == product and not f.free_good)
                    partner = (move_free_good + move_not_free_good).picking_id.partner_id
                    values.extend(self.get_value(
                        move_free_good=move_free_good,
                        move_not_free_good=move_not_free_good,
                        stt_key=stt_key,
                        date=split_key[1],
                        partner=(partner and partner[0]),
                        idx=idx,
                        dept_code=partner.property_account_cost_center_id.code
                    ))
                product_ids = product_ids - _product_ids

        for key, value in pos_values.items():
            split_key = key.split('_')
            sequence_key = split_key[0]
            sequence_stt = self.env['ir.sequence'].search([('code', '=', sequence_key)], limit=1)
            if not sequence_stt:
                vals = {
                    'name': 'Gom phiếu trả hàng POS: ' + sequence_key,
                    'code': sequence_key,
                    'company_id': None,
                    'prefix': sequence_key,
                    'padding': 7,
                    'number_increment': 1,
                    'number_next_actual': 1
                }
                sequence_stt = self.env['ir.sequence'].create(vals)
            product_ids = value.product_id
            while product_ids:
                _product_ids = product_ids[:1000]
                stt_key = sequence_stt._next()
                for idx, product in enumerate(_product_ids, start=1):
                    move_free_good = value.filtered(lambda f: f.product_id == product and f.free_good)
                    move_not_free_good = value.filtered(lambda f: f.product_id == product and not f.free_good)
                    store_id = (move_free_good + move_not_free_good).picking_id.pos_order_id.session_id.config_id.store_id
                    partner = store_id.contact_id
                    values.extend(self.get_value(
                        move_free_good=move_free_good,
                        move_not_free_good=move_not_free_good,
                        stt_key=stt_key,
                        date=split_key[1],
                        partner=(partner and partner[0]),
                        idx=idx,
                        dept_code=(store_id and store_id[0].analytic_account_id.code)
                    ))
                product_ids = product_ids - _product_ids

        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ phiếu nhập trả lại POS/SO nhanh tổng hợp", channel="root.Bravo").bravo_execute_query(insert_queries)

    @api.model
    def get_value(self, move_free_good, move_not_free_good, **kwargs):
        res = []
        for stock_move in (move_free_good, move_not_free_good):
            if not stock_move:
                continue
            account_move = stock_move.account_move_ids
            credit_lines = account_move.line_ids.filtered(lambda l: l.credit > 0)
            debit_lines = account_move.line_ids.filtered(lambda l: l.debit > 0)
            partner = kwargs.get('partner')
            company = stock_move.company_id and stock_move.company_id[0]
            warehouse_id = stock_move.location_dest_id.warehouse_id and stock_move.location_dest_id.warehouse_id[0]
            date = kwargs.get('date')
            stt_key = kwargs.get('stt_key') or None
            t_move = stock_move[0]
            qty_total = sum(stock_move.mapped('quantity_done'))
            amount_total = sum(debit_lines.mapped('debit'))
            credit_account = credit_lines.account_id and credit_lines.account_id[0].code or t_move.product_id.categ_id.with_company(self.env.company).property_stock_account_output_categ_id.code
            debit_account = debit_lines.account_id and debit_lines.account_id[0].code or t_move.product_id.categ_id.with_company(self.env.company).property_stock_valuation_account_id.code
            res.append({
                "CompanyCode": company.code or None,
                "Stt": stt_key,
                "DocCode": "TL",
                "DocNo": stt_key,
                "DocDate": date or None,
                "CurrencyCode": company.currency_id.name or None,
                "ExchangeRate": 1,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "TaxRegNo": partner.vat or None,
                "Description": f"Nhập kho hàng bán trả lại {warehouse_id.name} ngày {(t_move.date + timedelta(hours=7)).strftime('%d/%m/%Y')}",
                "EmployeeCode": None,
                "IsTransfer": 0,
                "PushDate": date or None,
                "BuiltinOrder": kwargs.get('idx'),
                "DebitAccount": debit_account or None,
                'ItemCode': t_move.product_id.barcode or None,
                'ItemName': t_move.product_id.name or None,
                'UnitPurCode': t_move.product_uom.code or None,
                "CreditAccount": credit_account or None,
                'Quantity9': qty_total,
                'ConvertRate9': 1,
                'Quantity': qty_total,
                'OriginalUnitCost': qty_total and amount_total / qty_total or 0,
                'UnitCost': qty_total and amount_total / qty_total or 0,
                "OriginalAmount": amount_total,
                "Amount": amount_total,
                "WarehouseCode": warehouse_id.code or None,
                "JobCode": stock_move.occasion_code_id and stock_move.occasion_code_id[0].code or None,
                "RowId": None,
                "DocNo_WO": stock_move.work_production and stock_move.work_production[0].code or None,
                "DeptCode": stock_move.account_analytic_id and stock_move.account_analytic_id[0].code or kwargs.get('dept_code') or None,
                "Stock_picking_id": ', '.join(map(str, stock_move.picking_id.ids))
            })
        return res

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.env['stock.picking'].bravo_get_picking_order_return_columns() + ['PushDate', 'Stock_picking_id']
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {}
