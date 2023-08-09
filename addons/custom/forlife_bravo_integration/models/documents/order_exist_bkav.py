# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class OrderExistBkav(models.Model):
    _inherit = 'account.move'

    def bravo_get_order_exist_bkav_values(self):
        res = []
        columns = self.bravo_get_order_exist_bkav_columns()
        for record in self:
            res.extend(record.bravo_get_order_exist_bkav_value())
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

    def bravo_get_order_exist_bkav_value(self):
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
            "EmployeeCode": self.user_id.employee_id.code or None,
            "IsTransfer": 0,
            "BuiltinOrder": 1,
            "DocumentType": None,
            "DebitAccount": debit_line.account_id.code or None,
            'ItemCode': 1,
            'ItemName': 1,
            'UnitPurCode': 1,
            "CreditAccount": credit_line.account_id.code or None,
            'Quantity9': 1,
            'ConvertRate9': 1,
            'Quantity': 1,
            'OriginalUnitCost': 1,
            'UnitCost': 1,
            "OriginalAmount": credit_line.credit,
            "Amount": credit_line.credit * self.exchange_rate,
            "WarehouseCode": picking.location_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
            "DeptCode": stock_move.account_analytic_id.code or None,
        }]
