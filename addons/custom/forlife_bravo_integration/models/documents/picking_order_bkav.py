# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import re


class PickingOrderBkav(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_order_bkav_values(self):
        res = []
        columns = self.bravo_get_picking_order_bkav_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            idx = 1
            for stock_move in record.move_ids:
                res.extend(record.bravo_get_picking_order_bkav_value(stock_move, employee.get('code'), idx))
                idx += 1
        return columns, res

    @api.model
    def bravo_get_picking_order_bkav_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "BuiltinOrder",
            "DebitAccount", "ItemCode", "ItemName", "UnitPurCode", "CreditAccount", "Quantity9", "ConvertRate9",
            "Quantity", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "WarehouseCode", "JobCode",
            "RowId", "DocNo_WO", "DeptCode",
        ]

    def bravo_get_picking_order_bkav_value(self, stock_move, employee_code, idx):
        account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
        debit_lines = account_move.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = account_move.line_ids.filtered(lambda l: l.credit > 0)
        debit_line = debit_lines and debit_lines[0]
        credit_line = credit_lines and credit_lines[0]
        exchange_rate = account_move.exchange_rate or 1
        if self.sale_id:
            partner = self.partner_id
        elif self.pos_order_id:
            partner = self.pos_order_id.session_id.config_id.store_id.contact_id
        else:
            partner = self.env['res.partner']
        return [{
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "PB",
            "DocNo": self.name or None,
            "DocDate": self.date_done or None,
            "CurrencyCode": self.company_id.currency_id.name or None,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": re.sub('<.*?>', '', self.note or '') or 'Xuất kho bán hàng',
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if account_move.is_tc else 0,
            "BuiltinOrder": idx,
            "DebitAccount": debit_line.account_id.code or stock_move.product_id.categ_id.with_company(self.company_id).property_stock_account_output_categ_id.code or None,
            'ItemCode': stock_move.product_id.barcode or None,
            'ItemName': stock_move.product_id.name or None,
            'UnitPurCode': stock_move.product_uom.code or None,
            "CreditAccount": credit_line.account_id.code or stock_move.product_id.categ_id.with_company(self.company_id).property_stock_valuation_account_id.code or None,
            'Quantity9': stock_move.quantity_done,
            'ConvertRate9': 1,
            'Quantity': stock_move.quantity_done,
            'OriginalUnitCost': debit_line.debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            'UnitCost': debit_line.debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "OriginalAmount": debit_line.debit,
            "Amount": debit_line.debit * exchange_rate,
            "WarehouseCode": self.location_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
            "DeptCode": stock_move.account_analytic_id.code or None,
        }]
