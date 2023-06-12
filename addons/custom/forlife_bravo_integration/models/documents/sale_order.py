# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def bravo_get_sale_order_values(self):
        pass

    def bravo_get_sale_order_columns(self):
        pass

    def bravo_get_sale_order_value(self):
        self.ensure_one()
        values = []
        invoice_lines = self.invoice_line_ids
        journal_lines = self.line_ids
        # the move has only one customer -> all invoice lines will have the same partner -> same receivable account
        receivable_lines = journal_lines.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        journal_lines = journal_lines - receivable_lines - invoice_lines
        receivable_lines = receivable_lines and receivable_lines[0]
        receivable_account_code = receivable_lines.account_id.code
        partner = self.partner_id
        exchange_rate = 0

        # FIXME: check fields : JobCode, ExchangeRate
        journal_value = {
            "CompanyCode": self.company_id.code,
            "DocCode": "H2",
            "DocNo": self.number_bills,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "TaxRegNo": partner.vat,
            "Description": self.invoice_description,
            "EmployeeCode": self.env.user.employee_id.code,
            "IsTransfer": 1 if self.x_asset_fin else 0,
            "DebitAccount": receivable_account_code,
            "DueDate": self.invoice_date_due,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                'BuiltinOrder': idx,
                "ItemCode": product.barcode,
                "ItemName": product.name,
                "CreditAccount2": invoice_line.account_id.code,
                "Quantity9": invoice_line.quantity,
                "ConvertRate9": 1,
                "Quantity": invoice_line.quantity,
                "PriceUnit": invoice_line.price_unit,

                "RowId": invoice_line.id
            })

            invoice_tax_ids = invoice_line.tax_ids
            # get journal line that matched tax with invoice line
            journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id and invoice_tax_ids)
            if journal_tax_lines:
                tax_line = journal_tax_lines[0]
                journal_value_line.update({
                    "TaxCode": tax_line.tax_line_id.code,
                    "OriginalAmount3": tax_line.tax_amount,
                    "Amount3": tax_line.tax_amount * exchange_rate,
                    "DebitAccount3": tax_line.account_id.code,
                    "CreditAccount3": receivable_account_code
                })

            values.append(journal_value_line)
        return values
