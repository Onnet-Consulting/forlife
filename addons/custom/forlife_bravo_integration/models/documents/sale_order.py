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
        exchange_rate = self.exchange_rate
        # FIXME: check fields : DebitAccount, DocumentType
        journal_value = {
            "CompanyCode": self.company_id.code,
            "DocCode": "H2",
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "TaxRegNo": partner.vat,
            "EmployeeCode": self.user_id.employee_id.code,
            "IsTransfer": 1 if self.x_asset_fin else 0,
            "DebitAccount": receivable_account_code
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                'BuiltinOrder': idx,
                "ItemCode": product.barcode,
                "ItemName": product.name,
            })
