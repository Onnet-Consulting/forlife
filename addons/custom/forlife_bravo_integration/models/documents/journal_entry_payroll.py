# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class JournalEntryPayroll(models.Model):
    _inherit = 'account.move'

    def bravo_get_journal_entry_payroll_values(self):
        res = []
        columns = self.bravo_get_journal_entry_payroll_columns()
        for record in self:
            res.extend(record.bravo_get_journal_entry_payroll_value())
        return columns, res

    @api.model
    def bravo_get_journal_entry_payroll_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "DocumentType",
            "BuiltinOrder", "DebitAccount", "CreditAccount", "OriginalAmount", "Amount", "DescriptionDetails",
            "JobCode", "RowId", "AssetCode", "DocNo_WO", "ExpenseCatgCode", "ProductCode", "DeptCode",
        ]

    def bravo_get_journal_entry_payroll_value(self):
        self.ensure_one()
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = self.line_ids.filtered(lambda l: l.credit > 0)
        if len(credit_lines) > 1:
            many_lines = credit_lines
            one_line = debit_lines and debit_lines[0]
        else:
            many_lines = debit_lines
            one_line = credit_lines and credit_lines[0]
        values = []
        stt = 1
        for line in many_lines:
            partner = line.partner_id or one_line.partner_id
            asset_id = line.asset_id or one_line.asset_id
            journal_value = {
                "CompanyCode": self.company_id.code or None,
                "Stt": self.name or None,
                "DocCode": "PK",
                "DocNo": self.name or None,
                "DocDate": self.date or None,
                "CurrencyCode": self.currency_id.name or None,
                "ExchangeRate": self.exchange_rate,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "Description": self.ref2 or None,
                "EmployeeCode": self.user_id.employee_id.code or None,
                "IsTransfer": 1 if self.x_asset_fin and self.x_asset_fin == 'TC' else 0,
                "DocumentType": None,
                "BuiltinOrder": stt,
                "DebitAccount": line.account_id.code if line.debit > 0 else one_line.account_id.code,
                "CreditAccount": line.account_id.code if line.credit > 0 else one_line.account_id.code or None,
                "OriginalAmount": max(line.debit, line.credit),
                "Amount": max(line.debit, line.credit) * self.exchange_rate,
                "DescriptionDetails": self.ref2 or None,
                "JobCode": line.occasion_code_id.code or one_line.occasion_code_id.code or None,
                "RowId": line.id or None,
                "AssetCode": asset_id.code if (asset_id and asset_id.type in ("CCDC", "TSCD")) else None,
                "DocNo_WO": line.work_order.code or one_line.work_order.code or None,
                "ExpenseCatgCode": line.expense_item_id.code or one_line.expense_item_id.code or None,
                "ProductCode": asset_id.code if (asset_id and asset_id.type == 'XDCB') else None,
                "DeptCode": line.analytic_account_id.code or one_line.analytic_account_id.code or None,
            }
            values.append(journal_value)
            stt += 1
        return values
