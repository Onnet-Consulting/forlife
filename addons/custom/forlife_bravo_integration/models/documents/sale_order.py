# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountDocSale(models.Model):
    _inherit = 'account.move'

    def bravo_get_account_doc_sale_values(self):
        res = []
        columns = self.bravo_get_account_doc_sale_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_account_doc_sale_value(employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_account_doc_sale_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "TaxRegNo", "Description", "EmployeeCode", "IsTransfer", "DebitAccount2",
            "DueDate", "BuiltinOrder", "ItemCode", "ItemName", 'UnitCode', "CreditAccount2", 'DebitAccount4',
            "Quantity9", "ConvertRate9", "Quantity", "PriceUnit", 'Amount4', 'OriginalAmount4',
            "TaxCode", "OriginalAmount3", "Amount3", 'UnitPrice', 'OriginalAmount2', 'CreditAccount4',
            "DebitAccount3", "CreditAccount3", "DocNo_SO", "RowId", 'OriginalUnitPrice', 'Amount2',
            "DocNo_WO", "DeptCode", "AssetCode", "ProductCode", "JobCode", 'EinvoiceItemType',
        ]

    def bravo_get_account_doc_sale_value(self, employee_code):
        self.ensure_one()
        values = []
        invoice_lines = self.invoice_line_ids
        tax_lines = self.line_ids.filtered(lambda l: l.display_type == 'tax')
        receivable_lines = self.line_ids - tax_lines - invoice_lines
        receivable_lines = receivable_lines and receivable_lines[0]
        receivable_account_code = receivable_lines.account_id.code or None
        partner = self.partner_id
        exchange_rate = 1

        journal_value = {
            "CompanyCode": self.company_id.code or None,
            'Stt': (self.is_post_bkav and self.invoice_no) or self.name or None,
            "DocCode": "H2",
            "DocNo": (self.is_post_bkav and self.invoice_no) or self.name or None,
            "DocDate": self.invoice_date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "TaxRegNo": partner.vat or None,
            "Description": self.invoice_description or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if self.is_tc else 0,
            "DebitAccount2": receivable_account_code,
            "PushDate": self.create_date or None,
            "DueDate": self.invoice_date_due or None,
        }

        idx = 0
        for idx, invoice_line in enumerate(invoice_lines, start=1):
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                'BuiltinOrder': idx,
                "ItemCode": product.barcode or None,
                "ItemName": product.name or None,
                "UnitCode": product.uom_id.code or None,
                "CreditAccount2": invoice_line.account_id.code or None,
                "Quantity9": invoice_line.quantity,
                "ConvertRate9": 1,
                "Quantity": invoice_line.quantity,
                "PriceUnit": invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity) or 0,
                "OriginalUnitPrice": invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity) or 0,
                'UnitPrice': invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity * exchange_rate) or 0,
                'OriginalAmount2': invoice_line.price_subtotal,
                'Amount2': invoice_line.price_subtotal * exchange_rate,
                'JobCode': invoice_line.occasion_code_id.code or None,
                "RowId": invoice_line.id,
                "DeptCode": invoice_line.analytic_account_id.code or partner.property_account_cost_center_id.code or None,
                "AssetCode": invoice_line.asset_code.code if (invoice_line.asset_code and invoice_line.asset_code.type in ("CCDC", "TSCD")) else None,
                "DocNo_SO": self.invoice_origin or None,
                "DocNo_WO": invoice_line.work_order.code or invoice_line.work_order.code or None,
                "ProductCode": (invoice_line.asset_id.type == 'XDCB' and invoice_line.asset_id.code) or (invoice_line.asset_code.type == 'XDCB' and invoice_line.asset_code.code) or None,
                "EinvoiceItemType": 3 if invoice_line.promotions else 1,
            })

            tax_line = invoice_line.tax_ids.invoice_repartition_line_ids.account_id
            if tax_line:
                tax_line = tax_line[0]
                original_amount3 = invoice_line.price_subtotal * invoice_line.tax_ids[0].amount / 100
                journal_value_line.update({
                    "TaxCode": invoice_line.tax_ids[0].code,
                    "OriginalAmount3": original_amount3,
                    "Amount3": original_amount3 * exchange_rate,
                    "DebitAccount3": tax_line.code,
                    "CreditAccount3": receivable_account_code
                })

            values.append(journal_value_line)

        for idx2, invoice_line in enumerate(self.promotion_ids.filtered(lambda f: f.promotion_type in ('vip_amount', 'customer_shipping_fee')), start=idx + 1):
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            item_code = {
                'vip_amount': 'THE',
                'customer_shipping_fee': 'SHIP',
            }
            quantity = 1
            convert_rate = 1
            journal_value_line.update({
                'BuiltinOrder': idx2,
                "ItemCode": item_code.get(invoice_line.promotion_type) or None,
                "ItemName": product.name or None,
                "UnitCode": product.uom_id.code or None,
                "CreditAccount2": invoice_line.account_id.code or None,
                "Quantity9": quantity,
                "ConvertRate9": convert_rate,
                "Quantity": quantity * convert_rate,
                "RowId": invoice_line.id,
                "DeptCode": partner.property_account_cost_center_id.code or None,
                "DocNo_SO": self.invoice_origin or None,
                "EinvoiceItemType": 2 if invoice_line.promotion_type == 'vip_amount' else 1,
            })

            tax_line = invoice_line.tax_id
            tax_line = tax_line and tax_line[0]
            tax = tax_line.amount / 100
            price_unit = invoice_line.value / (1 + tax)
            if tax_line:
                original_amount3 = price_unit * tax
                journal_value_line.update({
                    "TaxCode": tax_line.code,
                    "OriginalAmount3": original_amount3,
                    "Amount3": original_amount3 * exchange_rate,
                    "DebitAccount3": tax_line.invoice_repartition_line_ids.account_id.code,
                    "CreditAccount3": receivable_account_code
                })

            if invoice_line.promotion_type == 'customer_shipping_fee':
                journal_value_line.update({
                    "PriceUnit": price_unit,
                    "OriginalUnitPrice": price_unit,
                    'UnitPrice': price_unit * exchange_rate,
                    'OriginalAmount2': invoice_line.value,
                    'Amount2': invoice_line.value * exchange_rate,
                })
            if invoice_line.promotion_type == 'vip_amount':
                journal_value_line.update({
                    "DebitAccount4": invoice_line.account_id.code or None,
                    "CreditAccount4": partner.property_account_receivable_id.code or None,
                    "DebitAccount3": journal_value_line.get('CreditAccount3'),
                    "CreditAccount3": journal_value_line.get('DebitAccount3'),
                    "Amount4": price_unit,
                    "OriginalAmount4": price_unit * exchange_rate,
                })

            values.append(journal_value_line)
        return values

    @api.model
    def bravo_get_account_doc_sale_adjust_columns(self):
        return [
            'CompanyCode', 'Stt', 'DocCode', 'FormNo', 'DocNo', 'DocDate', 'CurrencyCode', 'ExchangeRate', 'CustomerCode', 'CustomerName', 'Address', 'TaxRegNo',
            'Description', 'EmployeeCode', 'IsTransfer', 'DueDate', 'EInvoiceTransType', 'EInvoiceOriginNo', 'OriginFormNo', 'BuiltinOrder', 'EinvoiceItemType',
            'DebitAccount2', 'CreditAccount2', 'ItemCode', 'ItemName', 'UnitCode', 'Quantity9', 'ConvertRate9', 'Quantity', 'OriginalUnitPrice', 'UnitPrice',
            'PriceUnit', 'Disscount', 'OriginalAmount2', 'Amount2', 'OriginalAmount4', 'Amount4', 'DebitAccount4', 'CreditAccount4', 'TaxCode', 'OriginalAmount3',
            'Amount3', 'DebitAccount3', 'CreditAccount3', 'DocNo_SO', 'JobCode', 'RowId', 'Assetcode', 'DepositCustomerCode', 'DocNo_WO', 'ProductCode', 'DeptCode',
        ]

    def bravo_get_sale_invoice_adjust_values(self, type=''):
        res = []
        columns = self.bravo_get_account_doc_sale_adjust_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id or self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_sale_invoice_adjust_value(employee.get('code'), type))
        return columns, res

    def bravo_get_sale_invoice_adjust_value(self, employee_code, type):
        self.ensure_one()
        values = []
        invoice_lines = self.invoice_line_ids
        tax_lines = self.line_ids.filtered(lambda l: l.display_type == 'tax')
        receivable_lines = self.line_ids - tax_lines - invoice_lines
        receivable_lines = receivable_lines and receivable_lines[0]
        receivable_account_code = receivable_lines.account_id.code or None
        partner = self.partner_id
        exchange_rate = self.exchange_rate
        value_by_type = {
            'increase': {
                'EInvoiceTransType': 'adjustIncrease',
                'EInvoiceOriginNo': self.debit_origin_id.invoice_no or self.debit_origin_id.name or None,
                'OriginFormNo': self.debit_origin_id.invoice_form or None,
            },
            'decrease': {
                'EInvoiceTransType': 'adjustDecrease',
                'EInvoiceOriginNo': self.origin_move_id.invoice_no or self.origin_move_id.name or None,
                'OriginFormNo': self.origin_move_id.invoice_form or None,
            },
        }

        journal_value = {
            "CompanyCode": self.company_id.code or None,
            'Stt': (self.is_post_bkav and self.invoice_no) or self.name or None,
            "DocCode": "HC",
            "FormNo": self.invoice_form if (self.is_post_bkav and self.invoice_no) else None,
            "DocNo": self.invoice_no or self.name or None,
            "DocDate": self.invoice_date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "TaxRegNo": partner.vat or None,
            "Description": self.invoice_description or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": self.invoice_no and 1 or 0,
            "PushDate": self.create_date or None,
            "DueDate": self.invoice_date_due or None,
            "EInvoiceTransType": value_by_type[type]['EInvoiceTransType'],
            "EInvoiceOriginNo": value_by_type[type]['EInvoiceOriginNo'],
            "OriginFormNo": value_by_type[type]['OriginFormNo'],
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                'BuiltinOrder': idx,
                "ItemCode": product.barcode or None,
                "ItemName": product.name or None,
                "UnitCode": product.uom_id.code or None,
                "CreditAccount2": (invoice_line.account_id.code if type == 'increase' else receivable_account_code) or None,
                "DebitAccount2": (receivable_account_code if type == 'increase' else invoice_line.account_id.code) or None,
                "Quantity9": invoice_line.quantity,
                "ConvertRate9": 1,
                "Quantity": invoice_line.quantity,
                "OriginalUnitPrice": invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity) or 0,
                'UnitPrice': invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity * exchange_rate) or 0,
                "PriceUnit": invoice_line.quantity and (invoice_line.price_subtotal / invoice_line.quantity) or 0,
                'Disscount': 0,
                'OriginalAmount2': invoice_line.price_subtotal,
                'Amount2': invoice_line.price_subtotal * exchange_rate,
                'OriginalAmount4': 0,
                'Amount4': 0,
                'JobCode': invoice_line.occasion_code_id.code or None,
                "RowId": invoice_line.id,
                "DeptCode": invoice_line.analytic_account_id.code or partner.property_account_cost_center_id.code or None,
                "DepositCustomerCode": invoice_line.asset_code.code if (invoice_line.asset_code and invoice_line.asset_code.type in ("CCDC", "TSCD")) else None,
                "DocNo_SO": self.invoice_origin or None,
                "DocNo_WO": invoice_line.work_order.code or invoice_line.work_order.code or None,
                "ProductCode": (invoice_line.asset_id.type == 'XDCB' and invoice_line.asset_id.code) or (invoice_line.asset_code.type == 'XDCB' and invoice_line.asset_code.code) or None,
                "EinvoiceItemType": 3 if invoice_line.promotions else 1,
            })
            tax_line = invoice_line.tax_ids.invoice_repartition_line_ids.account_id
            if tax_line:
                tax_line = tax_line[0]
                original_amount3 = invoice_line.price_subtotal * invoice_line.tax_ids[0].amount / 100
                journal_value_line.update({
                    "TaxCode": invoice_line.tax_ids[0].code,
                    "OriginalAmount3": original_amount3,
                    "Amount3": original_amount3 * exchange_rate,
                    "DebitAccount3": receivable_account_code if type == 'increase' else tax_line.code,
                    "CreditAccount3": tax_line.code if type == 'increase' else receivable_account_code,
                })

            values.append(journal_value_line)
        return values
