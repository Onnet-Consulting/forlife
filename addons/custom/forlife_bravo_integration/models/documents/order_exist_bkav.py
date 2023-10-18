# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class OrderExistBkav(models.Model):
    _inherit = 'account.move'

    def bravo_get_order_exist_bkav_values(self):
        res = []
        columns = self.bravo_get_order_exist_bkav_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_order_exist_bkav_value(employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_order_exist_bkav_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "BuiltinOrder", "DocumentType",
            "DebitAccount", "ItemCode", "ItemName", "UnitPurCode", "CreditAccount", "Quantity9", "ConvertRate9",
            "Quantity", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "WarehouseCode", "JobCode",
            "RowId", "DocNo_WO", "DeptCode",
        ]

    def bravo_get_order_exist_bkav_value(self, employee_code):
        self.ensure_one()
        stock_move = self.stock_move_id
        picking = stock_move.picking_id
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = self.line_ids.filtered(lambda l: l.credit > 0)
        debit_line = debit_lines and debit_lines[0]
        credit_line = credit_lines and credit_lines[0]
        if picking.sale_id:
            partner = picking.partner_id
        elif picking.pos_order_id:
            partner = picking.pos_order_id.session_id.config_id.store_id.contact_id
        else:
            partner = self.env['res.partner']
        return [{
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.name or None,
            "DocCode": "PB",
            "DocNo": picking.name or None,
            "DocDate": picking.date_done or None,
            "CurrencyCode": picking.company_id.currency_id.name or None,
            "ExchangeRate": self.exchange_rate,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.note or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": 0,
            "BuiltinOrder": 1,
            "DocumentType": None,
            "DebitAccount": debit_line.account_id.code or stock_move.product_id.categ_id.with_company(picking.company_id).property_stock_account_output_categ_id.code or None,
            'ItemCode': stock_move.product_id.barcode or None,
            'ItemName': stock_move.product_id.name or None,
            'UnitPurCode': stock_move.product_uom.name or None,
            "CreditAccount": credit_line.account_id.code or stock_move.product_id.categ_id.with_company(picking.company_id).property_stock_valuation_account_id.code or None,
            'Quantity9': stock_move.quantity_done,
            'ConvertRate9': 1,
            'Quantity': stock_move.quantity_done,
            'OriginalUnitCost': debit_line.debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            'UnitCost': debit_line.debit / stock_move.quantity_done if stock_move.quantity_done else 0,
            "OriginalAmount": debit_line.debit,
            "Amount": debit_line.debit * self.exchange_rate,
            "WarehouseCode": picking.location_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
            "DeptCode": stock_move.account_analytic_id.code or None,
        }]
