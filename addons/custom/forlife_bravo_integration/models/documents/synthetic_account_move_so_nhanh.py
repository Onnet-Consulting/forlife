# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class BravoSyntheticAccountMoveSoNhanh(models.Model):
    _name = 'synthetic.account.move.so.nhanh'
    _inherit = ['synthetic.account.move.so.nhanh', 'bravo.model.insert.action']
    _bravo_table = 'B30AccDocSales'

    is_bravo_pushed = fields.Boolean('Bravo pushed', default=False, copy=False)

    @api.model
    def sync_bravo_account_move_so_nhanh(self):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return False
        if self.env['ir.config_parameter'].sudo().get_param('bkav.is_general_bkav_nhanh'):
            domain = ['&', ('is_bravo_pushed', '=', False), ('data_compare_status', '=', '2')]
        else:
            domain = [('is_bravo_pushed', '=', False)]
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
                "Description": f"Tổng hợp bán hàng{line.invoice_date and line.invoice_date.strftime(' %d/%m/%Y') or ''}",
                "IsTransfer": 1 if line.invoice_no else 0,
                "DebitAccount2": account_receivable,
                "PushDate": line.create_date or None,
                "DueDate": line.invoice_date or None,
                "DeptCode": partner.property_account_cost_center_id.code or None,
            }
            idx = 0
            for idx, detail in enumerate(line.line_ids, start=1):
                value_line = copy.copy(value)
                convert_rate = 1
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": detail.barcode or None,
                    "ItemName": detail.product_id.name or None,
                    "UnitCode": detail.product_id.uom_id.code or None,
                    "CreditAccount2": detail.with_company(company).product_id.categ_id.property_account_income_categ_id.code or None,
                    "Quantity9": detail.quantity,
                    "ConvertRate9": convert_rate,
                    "Quantity": detail.quantity * convert_rate,
                    "PriceUnit": abs(detail.price_unit),
                    "OriginalUnitPrice": abs(detail.price_unit),
                    'UnitPrice': 0,
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
            products = self.env['product.product'].search([('barcode', 'in', ('DIEM', 'THE', 'SHIP'))])
            for idx, detail in enumerate(line.line_discount_ids, start=idx + 1):
                value_line = copy.copy(value)
                item_code = {'out_point': 'DIEM', 'vip_amount': 'THE', 'customer_shipping_fee': 'SHIP'}.get(detail.promotion_type) or ''
                product = products.filtered(lambda p: p.barcode == item_code)
                account_income = product.with_company(company).categ_id.property_account_income_categ_id.code or None
                tax_id = detail.tax_ids
                amount = detail.amount_total / (1 + (tax_id and tax_id[0].amount/100 or 0))
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": item_code,
                    "ItemName": product.name or None,
                    "UnitCode": product.uom_id.code or None,
                    "CreditAccount2": account_income,
                    "Quantity9": 1 if item_code == 'SHIP' else 0,
                    "ConvertRate9": 1,
                    "Quantity": 1 if item_code == 'SHIP' else 0,
                    "PriceUnit": abs(detail.price_unit) if item_code == 'SHIP' else 0,
                    "OriginalUnitPrice": abs(detail.price_unit) if item_code == 'SHIP' else 0,
                    'UnitPrice': abs(detail.price_unit) * exchange_rate if item_code == 'SHIP' else 0,
                    'OriginalAmount2': amount if item_code == 'SHIP' else 0,
                    'Amount2': amount * exchange_rate if item_code == 'SHIP' else 0,
                    "RowId": detail.id,
                    "EinvoiceItemType": 2,
                })
                if tax_id:
                    tax_line = tax_id and tax_id[0]
                    account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                    value_line.update({
                        "TaxCode": tax_line.code,
                        "OriginalAmount3": 0,
                        "Amount3": 0,
                        "DebitAccount3": account_receivable,
                        "CreditAccount3": account.code,
                    })
                if item_code in ('THE', 'DIEM'):
                    value_line.update({
                        "DebitAccount4": account_income,
                        "CreditAccount4": account_receivable,
                        "Amount4": amount,
                        "OriginalAmount4": amount * exchange_rate,
                    })

                values.append(value_line)
        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ xuất kho bán hàng tổng hợp NHANH", channel="root.Bravo").bravo_execute_query(insert_queries)
        if results:
            self._cr.execute(f"update synthetic_account_move_so_nhanh set is_bravo_pushed = true where id = any (array{results.ids})")

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.env['account.move'].bravo_get_account_doc_sale_columns()
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        date = self and self[0].create_date or False
        return {'PushDate': date or "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}
