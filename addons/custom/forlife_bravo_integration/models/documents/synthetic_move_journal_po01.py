# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class SyntheticMoveJournalPo01(models.TransientModel):
    _name = 'synthetic_move_journal_po01'
    _description = 'Synthetic Move Journal PI01'
    _inherit = 'bravo.model.insert.action'
    _bravo_table = 'B30AccDocInventory'

    def action_sync_data(self, moves, date):
        data = {}
        for m in moves:
            debit_line = m.line_ids.filtered(lambda l: l.debit > 0)
            credit_line = m.line_ids.filtered(lambda l: l.credit > 0)
            if len(m.line_ids) == 2 and '3387000001' in m.line_ids.account_id.mapped('code') and len(credit_line) == 1 and len(debit_line) == 1:
                key = credit_line.account_id.code + '|' + debit_line.account_id.code
                partner_id = (data.get(key) or {}).get('partner_id') or (m.line_ids.partner_id and m.line_ids.partner_id[0])
                occasion_code_id = (data.get(key) or {}).get('occasion_code_id') or (m.line_ids.occasion_code_id and m.line_ids.occasion_code_id[0])
                account_analytic_id = (data.get(key) or {}).get('account_analytic_id') or (m.line_ids.account_analytic_id and m.line_ids.account_analytic_id[0]) or (m.line_ids.analytic_account_id and m.line_ids.analytic_account_id[0])
                amount = ((data.get(key) or {}).get('amount') or 0) + max(credit_line.debit, credit_line.credit)
                val = {
                    'partner_id': partner_id,
                    'occasion_code_id': occasion_code_id,
                    'account_analytic_id': account_analytic_id,
                    'amount': amount,
                }
                data.update({
                    key: val
                })
        if data:
            data_insert = []
            exchange_rate = 1
            vals = {
                'CompanyCode': self.env.company.code or None,
                'DocCode': 'PK',
                'DocDate': date.strftime('%Y-%m-%d'),
                'CurrencyCode': self.env.company.currency_id.name or None,
                'ExchangeRate': exchange_rate,
                'Description': 'Ghi nhận tích điểm/tiêu điểm',
                'IsTransfer': 0,
            }
            idx = 1
            sequence_key = f"9754{date.strftime('%y')}"
            sequence_stt = self.env['ir.sequence'].search([('code', '=', sequence_key)], limit=1)
            if not sequence_stt:
                vals = {
                    'name': 'Gom bút toán tích điểm / tiêu điểm: ' + sequence_key,
                    'code': sequence_key,
                    'company_id': None,
                    'prefix': sequence_key,
                    'padding': 8,
                    'number_increment': 1,
                    'number_next_actual': 1
                }
                sequence_stt = self.env['ir.sequence'].create(vals)

            for k_item, v_item in data.items():
                x_vals = copy.copy(vals)
                account_code = k_item.split('|')
                partner_id = v_item.get('partner_id')
                occasion_code_id = v_item.get('occasion_code_id')
                account_analytic_id = v_item.get('account_analytic_id')
                amount = v_item.get('amount')
                x_vals.update({
                    'Stt': sequence_stt._next(),
                    'CustomerCode': partner_id.ref or None,
                    'CustomerName': partner_id.name or None,
                    'Address': partner_id.contact_address_complete or None,
                    'BuiltinOrder': idx,
                    'CreditAccount': account_code[0],
                    'DebitAccount': account_code[1],
                    'OriginalAmount': amount,
                    'Amount': amount * exchange_rate,
                    'JobCode': occasion_code_id.code or None,
                    'DeptCode': account_analytic_id.code or None,
                })
                data_insert.append(x_vals)
                idx += 1
            insert_queries = self.bravo_get_insert_sql(data=data_insert)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ gom bút toán tiêu/tích điểm ngày {date.strftime('%d/%m/%Y')}", channel="root.Bravo").bravo_execute_query(insert_queries)

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = [
            'CompanyCode', 'Stt', 'DocCode', 'DocDate', 'CurrencyCode', 'ExchangeRate', 'CustomerCode', 'CustomerName', 'Address', 'Description',
            'IsTransfer', 'BuiltinOrder', 'DebitAccount', 'CreditAccount', 'OriginalAmount', 'Amount', 'JobCode', 'DeptCode',
        ]
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}
