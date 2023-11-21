# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class EndingValuationAdjust(models.Model):
    _inherit = 'account.move'

    def bravo_get_ending_valuation_increase_values(self):
        res = []
        columns = self.env['stock.picking'].bravo_get_picking_other_import_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.get_ending_valuation_value(employee.get('code'), doc_code='PN', type_adjust='tăng'))
        return columns, res

    def bravo_get_ending_valuation_decrease_values(self):
        res = []
        columns = self.env['stock.picking'].bravo_get_picking_other_import_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.get_ending_valuation_value(employee.get('code'), doc_code='PX', type_adjust='giảm'))
        return columns, res

    def get_ending_valuation_value(self, employee_code, doc_code, type_adjust):
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = self.line_ids.filtered(lambda l: l.credit > 0)
        if len(credit_lines) > 1:
            many_lines = credit_lines
            one_line = debit_lines and debit_lines[0]
        elif len(debit_lines) > 1:
            many_lines = debit_lines
            one_line = credit_lines and credit_lines[0]
        else:
            if doc_code == 'PN':
                many_lines = debit_lines
                one_line = credit_lines and credit_lines[0]
            else:
                many_lines = credit_lines
                one_line = debit_lines and debit_lines[0]
        partner = self.partner_id or self.company_id.partner_id
        values = []
        for idx, line in enumerate(many_lines, start=1):
            product = line.product_id
            values.append({
                "CompanyCode": self.company_id.code or None,
                "Stt": self.name or None,
                "DocCode": doc_code,
                "DocNo": self.name or None,
                "DocDate": self.date or None,
                "CurrencyCode": self.company_id.currency_id.name or None,
                "ExchangeRate": 1,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "Description": self.invoice_description or f"Điều chỉnh {type_adjust} giá trị tồn kho",
                "EmployeeCode": employee_code or None,
                "IsTransfer": self.is_tc and 1 or 0,
                "BuiltinOrder": idx or None,
                "ItemCode": product.barcode or None,
                "ItemName": product.name or None,
                "UnitPurCode": product.uom_id.code or None,
                "Quantity9": 0,
                "ConvertRate9": 1,
                "Quantity": 0,
                "OriginalUnitCost": 0,
                "UnitCost": 0,
                "OriginalAmount": max(line.debit, line.credit),
                "Amount": max(line.debit, line.credit),
                "WarehouseCode": '1999',
                "JobCode": line.occasion_code_id.code or None,
                "DocNo_WO": line.work_order.code or line.production_order.code or None,
                "DeptCode": line.analytic_account_id.code or line.account_analytic_id.code or None,
                "RowId": line.id or None,
                "ProductCode": (line.asset_id.type == 'XDCB' and line.asset_id.code) or (line.asset_code.type == 'XDCB' and line.asset_code.code) or None,
                "ExpenseCatgCode": line.expense_item_id.code or one_line.expense_item_id.code or None,
                "AssetCode": (line.asset_id.type in ("CCDC", "TSCD") and line.asset_id.code) or (line.asset_code.type in ("CCDC", "TSCD") and line.asset_code.code) or None,
                "DebitAccount": line.account_id.code if line.debit > 0 else one_line.account_id.code,
                "CreditAccount": line.account_id.code if line.credit > 0 else one_line.account_id.code or None,
            })
        return values
