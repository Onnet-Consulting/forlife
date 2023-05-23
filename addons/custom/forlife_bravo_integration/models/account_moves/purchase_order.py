# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_asset_service_value(self):
        self.ensure_one()
        values = []
        column_names = [
            "CompanyCode", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "AtchDocDate", "AtchDocNo", "TaxRegName", "TaxRegNo",
            "EmployeeCode", "IsTransfer", "DueDate", "IsCompany", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9",
            "Quantity", "PriceUnit", "Discount", "OriginalUnitCost", "UnitCostCode", "OriginalAmount", "Amount",
            "IsPromotions", "DocNo_PO", "DeptCode", "DocNo_WO", "RowId",
            "TaxCode", "OriginalAmount3", "Amount3", "DebitAccount3", "CreditAccount3"

        ]
        journal_lines = self.line_ids
        invoice_lines = self.invoice_line_ids
        partner = self.partner_id
        is_partner_group_1 = partner.group_id == \
                             self.env.ref('forlife_pos_app_member.partner_group_1', raise_if_not_found=False)
        # the move has only one vendor -> all invoice lines will have the same partner -> same payable account
        payable_lines = journal_lines.filtered(lambda l: l.account_id.account_type == 'liability_payable')
        journal_lines = journal_lines - payable_lines - invoice_lines
        payable_line = payable_lines and payable_lines[0]
        payable_account_code = payable_line.account_id.code
        exchange_rate = self.exchange_rate

        journal_value = {
            "CompanyCode": self.company_id.code,
            "DocCode": "NK" if is_partner_group_1 else "NM",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": self.invoice_description,
            "AtchDocDate": self.date,
            "AtchDocNo": self.number_bills,
            "TaxRegName": partner.name,
            "TaxRegNo": partner.vat,
            "EmployeeCode": self.user_id.employee_id.code,
            "IsTransfer": 1 if self.x_asset_fin else 0,
            "DueDate": self.invoice_date_due,
            "IsCompany": (self.x_root == "Intel" and 1) or (self.x_root == "Winning" and 2) or 0,
            "CreditAccount": payable_account_code,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            purchase_order = invoice_line.purchase_order_id
            if not purchase_order:
                continue
            product = invoice_line.product_id
            journal_value.update({
                "BuiltinOrder": idx,
                "ItemCode": product.barcode,
                "ItemName": product.name,
                "UnitPurCode": invoice_line.product_uom_id.code,
                "DebitAccount": invoice_line.account_id.code,
                "Quantity9": invoice_line.quantity_purchased,
                "ConvertRate9": invoice_line.exchange_quantity,
                "Quantity": invoice_line.quantity,
                "PriceUnit": invoice_line.vendor_price,
                "Discount": invoice_line.discount,
                "OriginalUnitCost": invoice_line.vendor_price - invoice_line.discount,
                "UnitCostCode": (invoice_line.vendor_price - invoice_line.discount) * exchange_rate,
                "OriginalAmount": invoice_line.price_subtotal,
                "Amount": invoice_line.price_subtotal * exchange_rate,
                "IsPromotions": invoice_line.promotions,
                "DocNo_PO": purchase_order.name,
                "DeptCode": invoice_line.analytic_account_id.code,
                "DocNo_WO": invoice_line.work_order,
                "RowId": invoice_line.id
            })
            invoice_tax_ids = invoice_line.tax_ids
            # get journal line that matched tax with invoice line
            journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id & invoice_tax_ids)
            if journal_tax_lines:
                tax_line = journal_tax_lines[0]
                journal_value.update({
                    "TaxCode": tax_line.tax_line_id.code,
                    "OriginalAmount3": tax_line.tax_amount,
                    "Amount3": tax_line.tax_amount * exchange_rate,
                    "DebitAccount3": tax_line.account_id.code,
                    "CreditAccount3": payable_account_code
                })

            values.append(journal_value)

        return column_names, values
