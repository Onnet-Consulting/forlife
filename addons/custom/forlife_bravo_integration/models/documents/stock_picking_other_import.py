# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockPickingOtherImport(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_other_import_values(self):
        res = []
        columns = self.bravo_get_picking_other_import_columns()
        for record in self:
            res.extend(record.bravo_get_picking_other_import_value())
        return columns, res

    def bravo_get_picking_other_import_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "DocumentType", "BuiltinOrder",
            "CreditAccount", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9",
            "Quantity", "OriginalUnitCost", "UnitCostCode", "OriginalAmount", "Amount", "WarehouseCode", "JobCode",
            "RowId", "DocNo_WO", "DeptCode",
        ]

    def bravo_get_picking_other_import_value(self):
        count = 1
        values = []
        for stock_move in self.move_ids:
            for account_move in stock_move.account_move_ids:
                values.append(self.bravo_get_picking_other_import_by_account_move_value(account_move, count))
                count += 1
        return values

    def bravo_get_picking_other_import_by_account_move_value(self, account_move, line_count):
        stock_move = account_move.stock_move_id
        product = stock_move.product_id
        picking = stock_move.picking_id
        employee = self.env.user.employee_id
        partner = picking.partner_id or employee.partner_id
        journal_value = {
            "CompanyCode": picking.company_id.code,
            "Stt": picking.name,
            "DocCode": "TP" if picking.reason_type_id.code == 'N01' else 'PN',
            "DocNo": picking.name,
            "DocDate": picking.date_done,
            "CurrencyCode": self.env.company.currency_id.name,
            "ExchangeRate": 1,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": picking.note,
            "EmployeeCode": employee.code,
            "IsTransfer": 0,
            "DocumentType": picking.location_id.code,
            "BuiltinOrder": line_count,
            "ItemCode": product.barcode,
            "ItemName": product.name,
            "UnitPurCode": stock_move.product_uom.code,
            "Quantity9": stock_move.quantity_done,
            "ConvertRate9": 1,
            "Quantity": stock_move.quantity_done,
            "OriginalUnitCost": stock_move.price_unit,
            "UnitCostCode": stock_move.price_unit,
            "OriginalAmount": stock_move.price_unit * stock_move.quantity_done,
            "Amount": stock_move.price_unit * stock_move.quantity_done,
            "WarehouseCode": picking.location_dest_id.warehouse_id.code,
            "JobCode": stock_move.occasion_code_id.code,
            "DocNo_WO": stock_move.work_production.code,
            'DeptCode': stock_move.account_analytic_id.code,
            "RowId": stock_move.id,
        }

        for move_line in account_move.line_ids:
            if move_line.debit:
                journal_value.update({
                    'DebitAccount': move_line.account_id.code
                })
            else:
                journal_value.update({
                    'CreditAccount': move_line.account_id.code
                })

        return journal_value
