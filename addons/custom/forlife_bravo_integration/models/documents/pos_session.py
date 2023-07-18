# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosSessionCashInMove(models.Model):
    _inherit = 'account.move'

    def bravo_get_cash_in_move_values(self):
        res = []
        columns = self.bravo_get_cash_in_move_columns()
        for record in self:
            res.extend(record.bravo_get_cash_in_move_value())
        return columns, res

    @api.model
    def bravo_get_cash_in_move_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "BuiltinOrder", "DebitAccount", "CreditAccount",
            "OriginalAmount", "Amount", "Description1", "RowId", "DeptCode"
        ]

    def bravo_get_cash_in_move_value(self):
        self.ensure_one()
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        debit_line = debit_lines and debit_lines[0]
        credit_lines = self.line_ids - debit_lines
        credit_line = credit_lines and credit_lines[0]
        exchange_rate = 1
        store_id = self.statement_line_id.pos_session_id.config_id.store_id
        analytic_account = store_id.analytic_account_id
        partner = debit_line.partner_id or credit_line.partner_id or store_id.contact_id
        values = []
        journal_value = {
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "PT",
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": debit_line.name or None,
            "EmployeeCode": self.env.user.employee_id.code or None,
            "BuiltinOrder": 1,
            "DebitAccount": debit_line.account_id.code or None,
            "CreditAccount": credit_line.account_id.code or None,
            "OriginalAmount": debit_line.debit,
            "Amount": debit_line.debit,
            "Description1": debit_line.name or None,
            "DeptCode": analytic_account.code or None,
            "RowId": debit_line.id or None
        }
        values.append(journal_value)
        return values


class PosSessionCashOutMove(models.Model):
    _inherit = 'account.move'

    def bravo_get_cash_out_move_values(self):
        res = []
        columns = self.bravo_get_cash_out_move_columns()
        for record in self:
            res.extend(record.bravo_get_cash_out_move_value())
        return columns, res

    @api.model
    def bravo_get_cash_out_move_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "BuiltinOrder", "DebitAccount",
            "CreditAccount", "OriginalAmount", "Amount", "Description1", "DeptCode", "RowId",
        ]

    def bravo_get_cash_out_move_value(self):
        self.ensure_one()
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        debit_line = debit_lines and debit_lines[0]
        credit_lines = self.line_ids - debit_lines
        credit_line = credit_lines and credit_lines[0]
        exchange_rate = 1
        store_id = self.statement_line_id.pos_session_id.config_id.store_id
        analytic_account = store_id.analytic_account_id
        partner = debit_line.partner_id or credit_line.partner_id or store_id.contact_id
        values = []
        journal_value = {
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "PC",
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": debit_line.name or None,
            "EmployeeCode": self.env.user.employee_id.code or None,
            "BuiltinOrder": 1,
            "DebitAccount": debit_line.account_id.code or None,
            "CreditAccount": credit_line.account_id.code or None,
            "OriginalAmount": debit_line.debit,
            "Amount": debit_line.debit,
            "Description1": debit_line.name or None,
            "DeptCode": analytic_account.code or None,
            "RowId": debit_line.id or None
        }
        values.append(journal_value)
        return values
