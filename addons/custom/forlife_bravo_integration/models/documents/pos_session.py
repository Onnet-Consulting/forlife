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
        partner = debit_line.partner_id
        exchange_rate = 1
        values = []
        journal_value = {
            "CompanyCode": self.company_id.code,
            "Stt": self.name,
            "DocCode": "PT",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": self.name,
            "EmployeeCode": self.env.user.employee_id.code,
            "BuiltinOrder": 1,
            "DebitAccount": debit_line.account_id.code,
            "CreditAccount": credit_line.account_id.code,
            "OriginalAmount": debit_line.debit,
            "Amount": debit_line.debit,
            "Description1": debit_line.name,
            "DeptCode": debit_line.account_analytic_id.code,
            "RowId": debit_line.id
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
        return []

    def bravo_get_cash_out_move_value(self):
        self.ensure_one()
        values = []

        return values
