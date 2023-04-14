# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

CONTEXT_JOURNAL_ACTION = 'bravo_journal_action'


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'bravo.model.insert.action']

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        posted_moves = self.filtered(lambda m: m.state == 'posted')
        insert_queries = posted_moves.bravo_get_insert_sql()
        self.env[self._name].sudo().with_delay().bravo_insert(insert_queries)
        return res

    @api.model
    def bravo_get_table(self):
        journal_action = self.env.context.get(CONTEXT_JOURNAL_ACTION)
        bravo_table = 'DEFAULT'
        if journal_action == 'purchase_journal':
            bravo_table = 'B30AccDocOther'
        return bravo_table

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def get_sale_bill_data(self):
        move_lines = self.mapped('invoice_line_ids').filtered(lambda ml: ml.sale_line_ids)
        bravo_column_names = []
        moves_data = []
        for idx, line in enumerate(move_lines, start=1):
            move = line.move_id
            move_partner = move.partner_id
            bravo_data = {
                "CompanyCode": move.company_id.code,
                "Stt": line.id,
                "DocCode": "H2",
                "DocDate": move.invoice_date,
                "CurrencyCode": move.currency_id.name,
                "ExchangeRate": move.currency_id.rate,
                "CustomerCode": move_partner.ref,
                "CustomerName": move_partner.name,
                "Address": move_partner.contact_address_complete,
                "TaxRegNo": move_partner.vat,
                "EmployeeCode": move.invoice_user_id.employee_id.code,
            }

    def get_purchase_journal_data(self):
        move_lines = self.mapped('line_ids').filtered(lambda ml: ml.purchase_line_id)
        bravo_column_names = []
        moves_data = []
        for idx, line in enumerate(move_lines, start=1):
            move = line.move_id
            credit_line = move.line_ids.filtered(lambda m:m.credit>0)
            if not credit_line:
                continue
            credit_line = credit_line[0]
            tax_line = (move.line_ids - credit_line).filtered(lambda m: m.tax_line_id)
            tax_line = tax_line[0] if tax_line else False
            move_partner = move.partner_id
            bravo_data = {
                "CompanyCode": move.company_id.code,
                "Stt": move.id,
                "DocCode": "BT",
                "DocNo": move.name,
                "DocDate": move.invoice_date,
                "CurrencyCode": move.currency_id.name,
                "CustomerCode": move_partner.ref,
                "CustomerName": move_partner.name,
                "Address": move_partner.contact_address_complete,
                "EmployeeCode": move.invoice_user_id.employee_id.code,
                "BuiltinOrder": idx,
                "DebitAccount": line.account_id.code,
                "CreditAccount3": line.account_id.code,
                "CreditAccount": credit_line.account_id.code,
                "DebitAccount3": tax_line.account_id.code if tax_line else False,
                "TaxCode": tax_line.tax_line_id.code if tax_line else False,
                "OriginalAmount": line.price_subtotal,
                'OriginalAmount3': line.price_total - line.price_subtotal,
                'RowId': line.id
            }
            moves_data.append(bravo_data)
            if bravo_column_names:
                continue
            bravo_column_names = list(bravo_data.keys())

        return bravo_column_names, moves_data

    def bravo_get_insert_values(self):
        journal_type = self.env.context.get(CONTEXT_JOURNAL_ACTION)
        if journal_type == 'purchase_journal':
            return self.get_purchase_journal_data()
        return [], []

    def bravo_get_insert_sql_by_journal_action(self):
        queries = []
        purchase_journal_query = self.with_context(
            **{CONTEXT_JOURNAL_ACTION: 'purchase_journal'}).bravo_get_insert_sql()
        if purchase_journal_query:
            queries.extend(purchase_journal_query)
        return queries

    def bravo_get_insert_sql(self):
        if self.env.context.get(CONTEXT_JOURNAL_ACTION):
            return super().bravo_get_insert_sql()
        return self.bravo_get_insert_sql_by_journal_action()