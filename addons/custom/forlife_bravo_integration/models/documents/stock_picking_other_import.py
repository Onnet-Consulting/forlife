# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockPickingOtherImport(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_other_import_values(self):
        res = []
        columns = self.bravo_get_picking_other_import_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_picking_other_import_value(employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_picking_other_import_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "DocumentType", "BuiltinOrder",
            "CreditAccount", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9",
            "Quantity", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "WarehouseCode", "JobCode",
            "RowId", "DocNo_WO", "DeptCode", "ProductCode", "ExpenseCatgCode", "AssetCode",
        ]

    def bravo_get_picking_other_import_value(self, employee_code):
        count = 1
        values = []
        for stock_move in self.move_ids:
            account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
            values.append(self.bravo_get_picking_other_import_by_account_move_value(stock_move, account_move, count, employee_code))
            count += 1
        return values

    def bravo_get_picking_other_import_by_account_move_value(self, stock_move, account_move, line_count, employee_code):
        product = stock_move.product_id
        picking = stock_move.picking_id
        employee = self.env.user.sudo().employee_id
        partner = picking.partner_id or self.env.company.partner_id or employee.partner_id
        account_move_lines = account_move.line_ids
        debit_lines = account_move_lines.filtered(lambda x: x.debit > 0)
        credit_lines = account_move_lines - debit_lines
        debit_line = debit_lines[0] if debit_lines else debit_lines
        credit_line = credit_lines[0] if credit_lines else credit_lines
        debit = debit_line.debit if debit_line else 0
        debit_account_code = debit_line.account_id.code if debit_line else stock_move.product_id.categ_id.with_company(picking.company_id).property_stock_valuation_account_id.code
        credit_account_code = credit_line.account_id.code if credit_line else picking.location_id.x_property_valuation_in_account_id.code
        quantity_done = stock_move.quantity_done

        journal_value = {
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.name or None,
            "DocCode": "TP" if picking.sudo().reason_type_id.code == 'N01' else 'PN',
            "DocNo": picking.name or None,
            "DocDate": picking.date_done or None,
            "CurrencyCode": self.env.company.currency_id.name or None,
            "ExchangeRate": 1,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.note or picking.location_id.name or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": 0,
            "DocumentType": picking.location_id.code or None,
            "BuiltinOrder": line_count or None,
            "ItemCode": product.barcode or None,
            "ItemName": product.name or None,
            "UnitPurCode": stock_move.product_uom.code or None,
            "Quantity9": quantity_done,
            "ConvertRate9": 1,
            "Quantity": quantity_done,
            "OriginalUnitCost": debit / quantity_done if quantity_done else 0,
            "UnitCost": debit / quantity_done if quantity_done else 0,
            "OriginalAmount": debit,
            "Amount": debit,
            "WarehouseCode": picking.location_dest_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "DocNo_WO": stock_move.work_production.code or None,
            'DeptCode': stock_move.account_analytic_id.code or None,
            "RowId": stock_move.id or None,
            "DebitAccount": debit_account_code or None,
            "CreditAccount": credit_account_code or None,
        }

        return journal_value
