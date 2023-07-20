# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta


class StockPickingTransferBkav(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_transfer_bkav_values(self):
        res = []
        columns = self.bravo_get_picking_transfer_bkav_columns()
        for record in self:
            res.extend(record.bravo_get_picking_transfer_bkav_value())
        return columns, res

    @api.model
    def bravo_get_picking_transfer_bkav_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "DeptCode", "IsTransfer", "ReceiptWarehouseCode",
            "BuiltinOrder", "CreditAccount", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9",
            "Quantity", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "WarehouseCode", "RowId", "DocNo_WO",
        ]

    def bravo_get_picking_transfer_bkav_value(self):
        count = 1
        values = []
        for stock_move in self.move_ids:
            account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
            values.append(self.bravo_get_picking_transfer_bkav_by_account_move_value(stock_move, account_move, count))
            count += 1
        return values

    def bravo_get_picking_transfer_bkav_by_account_move_value(self, stock_move, account_move, line_count):
        product = stock_move.product_id
        picking = stock_move.picking_id
        employee = picking.user_id.employee_id
        partner = picking.partner_id or picking.user_id.partner_id
        debit_line = account_move.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
        credit = credit_line[0].credit if credit_line else 0
        journal_value = {
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.name or None,
            "DocCode": 'DC',
            "DocNo": picking.name or None,
            "DocDate": picking.date_done and (picking.date_done + timedelta(days=7)).strftime('%Y-%m-%d') or None,
            "CurrencyCode": self.env.company.currency_id.name or None,
            "ExchangeRate": 1,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.transfer_id.note or 'Xuất điều chuyển nội bộ',
            "EmployeeCode": employee.code or None,
            'DeptCode': picking.transfer_id and picking.transfer_id.department_id.center_expense_id.code or None,
            "IsTransfer": 0,
            "ReceiptWarehouseCode": picking.location_dest_id.code or None,
            "BuiltinOrder": line_count or None,
            "CreditAccount": credit_line[0].account_id.code if credit_line else (product.categ_id.property_stock_valuation_account_id.code or None),
            "ItemCode": product.barcode or None,
            "ItemName": product.name or None,
            "UnitPurCode": stock_move.product_uom.code or None,
            "DebitAccount": debit_line[0].account_id.code if debit_line else (product.categ_id.property_stock_valuation_account_id.code or None),
            "Quantity9": stock_move.quantity_done or 0,
            "ConvertRate9": 1,
            "Quantity": stock_move.quantity_done or 0,
            "OriginalUnitCost": credit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "UnitCost": credit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "OriginalAmount": credit,
            "Amount": credit,
            "WarehouseCode": picking.location_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
        }

        return journal_value
