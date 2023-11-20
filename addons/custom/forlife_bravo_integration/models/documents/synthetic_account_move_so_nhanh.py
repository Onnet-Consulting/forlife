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

            discounts = {}
            for d in line.line_discount_ids:
                tax = d.tax_ids.ids or ['']
                x_price_unit = d.price_unit if d.promotion_type == 'customer_shipping_fee' else 0
                x_amount_total = d.amount_total
                key = f"{d.promotion_type}~{tax[0]}"
                old_val = discounts.get(key) or {}
                promotion_type = old_val.get('promotion_type') or d.promotion_type
                price_unit = (old_val.get('price_unit') or 0) + x_price_unit
                amount_total = (old_val.get('amount_total') or 0) + x_amount_total
                tax_amount = old_val.get('tax_amount') or (d.tax_ids.mapped('amount') or [0])[0]
                tax_code = old_val.get('tax_code') or (d.tax_ids.mapped('code') or [''])[0]
                account = old_val.get('account') or (d.tax_ids.invoice_repartition_line_ids.account_id.mapped('code') or [''])[0]
                original_amount3 = (old_val.get('original_amount3') or 0) + d.tax_amount
                discounts.update({
                    key: {
                        'promotion_type': promotion_type,
                        'price_unit': price_unit,
                        'amount_total': amount_total,
                        'tax_amount': tax_amount,
                        'tax_code': tax_code,
                        'account': account,
                        'original_amount3': original_amount3,
                    }
                })

            products = self.env['product.product'].search([('barcode', 'in', ('DIEM', 'THE', 'SHIP'))])
            for idx, detail in enumerate(discounts.values(), start=idx + 1):
                value_line = copy.copy(value)
                promotion_type = detail.get('promotion_type') or ''
                item_code = {'out_point': 'DIEM', 'vip_amount': 'THE', 'customer_shipping_fee': 'SHIP'}.get(promotion_type) or ''
                product = products.filtered(lambda p: p.barcode == item_code)
                account_income = product.with_company(company).categ_id.property_account_income_categ_id.code or None
                amount = (detail.get('amount_total') or 0) / (1 + ((detail.get('tax_amount') or 0) / 100))
                hs = 1 if item_code == 'SHIP' else -1
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": item_code,
                    "ItemName": product.name or None,
                    "UnitCode": product.uom_id.code or None,
                    "CreditAccount2": account_income,
                    "Quantity9": 1 if item_code == 'SHIP' else 0,
                    "ConvertRate9": 1,
                    "Quantity": 1 if item_code == 'SHIP' else 0,
                    "PriceUnit": detail.get('price_unit') or 0,
                    "OriginalUnitPrice": detail.get('price_unit') or 0,
                    'UnitPrice': (detail.get('price_unit') or 0) * exchange_rate,
                    'OriginalAmount2': amount if item_code == 'SHIP' else 0,
                    'Amount2': amount * exchange_rate if item_code == 'SHIP' else 0,
                    "RowId": None,
                    "EinvoiceItemType": 2,
                    "OriginalAmount3": (detail.get('original_amount3') or 0) * hs,
                    "Amount3": (detail.get('original_amount3') or 0) * exchange_rate * hs,
                })
                if detail.get('tax_code'):
                    value_line.update({
                        "TaxCode": detail.get('tax_code'),
                        "DebitAccount3": account_receivable,
                        "CreditAccount3": detail.get('account') or None,
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
        return {'PushDate': self and self[0].create_date or "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}
