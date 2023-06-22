# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockPickingOtherExport(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_other_export_values(self):
        res = []
        columns = self.bravo_get_picking_other_export_columns()
        for record in self:
            res.extend(record.bravo_get_picking_other_export_value())
        return columns, res

    @api.model
    def bravo_get_picking_other_export_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "EmployeeCode", "IsTransfer", "BuiltinOrder", "DocumentType", "DebitAccount",
            "ItemCode", "ItemName", "UnitPurCode", "CreditAccount", "Quantity9", "ConvertRate9", "Quantity",
            "OriginalUnitCost", "UnitCostCode", "OriginalAmount", "Amount", "WarehouseCode", "JobCode", "RowId",
            "DocNo_WO", "ProductCode", "DeptCode",
        ]

    def bravo_get_picking_other_export_value(self):
        count = 1
        values = []
        for stock_move in self.move_ids:
            account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
            values.append(self.bravo_get_picking_other_export_by_account_move_value(stock_move, account_move, count))
            count += 1
        return values

    def bravo_get_picking_other_export_by_account_move_value(self, stock_move, account_move, line_count):
        product = stock_move.product_id
        picking = stock_move.picking_id
        employee = self.env.user.employee_id
        partner = picking.partner_id or employee.partner_id
        debit_line = account_move.line_ids.filtered(lambda l: l.debit > 0)
        debit_line = debit_line[0] if debit_line else False
        debit = debit_line.debit if debit_line else 0
        credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
        credit_line = credit_line[0] if credit_line else False
        credit_account_code = credit_line.account_id.code if credit_line else False
        debit_account_code = debit_line.account_id.code if debit_line else False
        journal_value = {
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.id or None,
            "DocCode": 'PX',
            "DocNo": picking.name or None,
            "DocDate": picking.date_done or None,
            "CurrencyCode": self.env.company.currency_id.name or None,
            "ExchangeRate": 1,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "EmployeeCode": employee.code or None,
            "IsTransfer": 0,
            "BuiltinOrder": line_count or None,
            "DocumentType": picking.location_dest_id.code or None,
            "ItemCode": product.barcode or None,
            "ItemName": product.name or None,
            "UnitPurCode": stock_move.product_uom.code or None,
            "Quantity9": stock_move.quantity_done,
            "ConvertRate9": 1,
            "Quantity": stock_move.quantity_done,
            "OriginalUnitCost": debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "UnitCostCode": debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "OriginalAmount": debit,
            "Amount": debit,
            "WarehouseCode": picking.location_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "DocNo_WO": stock_move.work_production.code or None,
            'DeptCode': stock_move.account_analytic_id.code or None,
            "RowId": stock_move.id or None,
            "DebitAccount": debit_account_code or None,
            "CreditAccount": credit_account_code or None,
        }

        return journal_value
