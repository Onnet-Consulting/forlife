# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class BravoSyntheticAccountMovePos(models.Model):
    _name = 'synthetic.account.move.pos'
    _inherit = ['synthetic.account.move.pos', 'bravo.model.insert.action']
    _bravo_table = 'B30AccDocSales'

    is_bravo_pushed = fields.Boolean('Bravo pushed', default=False, copy=False)

    @api.model
    def sync_bravo_account_move_pos(self):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return False
        domain = ['&', ('is_bravo_pushed', '=', False), '|', ('store_id.is_post_bkav', '=', False),
                  '&', ('store_id.is_post_bkav', '=', True), ('data_compare_status', '=', '2')]
        results = self.search(domain)
        values = []
        exchange_rate = 1
        for line in results:
            partner = line.partner_id
            company = line.company_id
            account_receivable = partner.property_account_receivable_id.code or None
            value = {
                "CompanyCode": company.code or None,
                'Stt': line.code or None,
                "DocCode": "H2",
                "DocNo": line.code or None,
                "DocDate": line.invoice_date or None,
                "CurrencyCode": company.currency_id.name or None,
                "ExchangeRate": exchange_rate,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "TaxRegNo": partner.vat or None,
                "Description": f"Tổng hợp bán hàng {line.store_id.name or ''}",
                "IsTransfer": 1 if line.store_id.is_post_bkav else 0,
                "DebitAccount2": account_receivable,
                "DueDate": line.invoice_date or None,
                "DeptCode": line.store_id.analytic_account_id.code or None,
            }
            idx = 0
            for idx, detail in enumerate(line.line_ids, start=1):
                value_line = copy.copy(value)
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": detail.barcode or None,
                    "ItemName": detail.product_id.name or None,
                    "UnitCode": detail.product_id.uom_id.code or None,
                    "CreditAccount2": detail.with_company(company).product_id.categ_id.property_account_income_categ_id.code or None,
                    "Quantity9": detail.quantity,
                    "ConvertRate9": 1,
                    "Quantity": detail.quantity,
                    "PriceUnit": abs(detail.price_unit),
                    "OriginalUnitPrice": abs(detail.price_unit),
                    'UnitPrice': abs(detail.price_unit) * exchange_rate,
                    'OriginalAmount2': abs(detail.price_subtotal),
                    'Amount2': abs(detail.price_subtotal) * exchange_rate,
                    "RowId": detail.id,
                    "EinvoiceItemType": 3 if detail.x_free_good else 1,
                })
                tax_id = detail.tax_ids
                if tax_id:
                    tax_line = tax_id and tax_id[0]
                    original_amount3 = abs(detail.price_subtotal) * tax_line.amount / 100
                    account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                    value_line.update({
                        "TaxCode": tax_line.code,
                        "OriginalAmount3": original_amount3,
                        "Amount3": original_amount3 * exchange_rate,
                        "DebitAccount3": account_receivable,
                        "CreditAccount3": account.code,
                    })
                values.append(value_line)
            products = self.env['product.product'].search([('barcode', 'in', ('DIEM', 'THE'))])
            for idx, detail in enumerate(line.discount_ids.filtered(lambda f: f.promotion_type in ('point', 'card')), start=idx + 1):
                value_line = copy.copy(value)
                item_code = {'point': 'DIEM', 'card': 'THE'}.get(detail.promotion_type) or ''
                product = products.filtered(lambda p: p.barcode == item_code)
                account_income = product.with_company(company).categ_id.property_account_income_categ_id.code or None
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": item_code,
                    "ItemName": product.name or None,
                    "UnitCode": product.uom_id.code or None,
                    "CreditAccount2": account_income,
                    "DebitAccount4": account_income,
                    "CreditAccount4": account_receivable,
                    "Quantity9": 0,
                    "ConvertRate9": 0,
                    "Quantity": 0,
                    "PriceUnit": 0,
                    "OriginalUnitPrice": 0,
                    'UnitPrice': 0,
                    'OriginalAmount2': 0,
                    'Amount2': 0,
                    "RowId": detail.id,
                    "EinvoiceItemType": 2,
                    "Amount4": abs(detail.price_unit),
                    "OriginalAmount4": abs(detail.price_unit) * exchange_rate,
                    "OriginalAmount3": detail.tax_amount,
                    "Amount3": detail.tax_amount * exchange_rate,
                })
                tax_id = detail.tax_ids
                if tax_id:
                    tax_line = tax_id and tax_id[0]
                    account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                    value_line.update({
                        "TaxCode": tax_line.code,
                        "DebitAccount3": account_receivable,
                        "CreditAccount3": account.code,
                    })
                values.append(value_line)
        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ xuất kho bán hàng tổng hợp POS", channel="root.Bravo").bravo_execute_query(insert_queries)
        if results:
            self._cr.execute(f"update synthetic_account_move_pos set is_bravo_pushed = true where id = any (array{results.ids})")

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.env['account.move'].bravo_get_account_doc_sale_columns()
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {'PushDate': self and self[0].create_date or "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}
