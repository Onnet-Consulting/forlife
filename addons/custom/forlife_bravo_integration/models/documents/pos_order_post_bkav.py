# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class PosOrderPostBkav(models.AbstractModel):
    _name = 'pos.order.post.bkav'
    _inherit = 'bravo.model.insert.action'
    _bravo_table = "B30AccDocSales"

    def sync_bravo_pos_order_post_bkav(self):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return False
        domain = ['&', ('is_bravo_pushed1', '=', False), '&', ('is_post_bkav', '=', True), ('is_refund_order', '!=', True)]
        records = self.env['pos.order'].search(domain)
        values = []
        for order in records:
            company = order.company_id
            partner = order.store_id.contact_id
            account_receivable = partner.property_account_receivable_id.code or None
            value = {
                "CompanyCode": company.code or None,
                'Stt': order.invoice_no or None,
                "DocCode": "H2",
                "DocNo": order.invoice_no or None,
                "DocDate": order.invoice_e_date or None,
                "CurrencyCode": company.currency_id.name or None,
                "ExchangeRate": 1,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "TaxRegNo": partner.vat or None,
                "Description": f"Bán hàng {order.store_id.name or ''}",
                "EmployeeCode": None,
                "IsTransfer": 1 if order.store_id.is_post_bkav else 0,
                "DebitAccount2": account_receivable,
                "DebitAccount3": account_receivable,
                "PushDate": order.invoice_e_date or "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
                "DueDate": order.invoice_e_date or None,
                "DeptCode": order.store_id.analytic_account_id.code or None,
            }
            idx = 0
            for idx, line in enumerate(order.lines.filtered_domain([('qty', '>', 0), ('promotion_type', '=', False)]), start=1):
                value_line = copy.copy(value)
                product = line.product_id
                tax_id = line.tax_ids_after_fiscal_position and line.tax_ids_after_fiscal_position[0]
                account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                original_unit_price = (line.original_price - sum(line.discount_details_lines.filtered(lambda f: f.type not in ('card', 'point')).mapped('money_reduced'))) / (1 + tax_id.amount / 100)
                original_amount3 = original_unit_price * line.qty * tax_id.amount / 100
                value_line.update({
                    'CreditAccount2': product.with_company(company).categ_id.property_account_income_categ_id.code or None,
                    'BuiltinOrder': idx,
                    "ItemCode": line.product_id.barcode or None,
                    "ItemName": line.product_id.name or None,
                    "UnitCode": line.product_id.uom_id.code or None,
                    "Quantity9": line.qty,
                    "ConvertRate9": 1,
                    "Quantity": line.qty,
                    "PriceUnit": original_unit_price,
                    "OriginalUnitPrice": original_unit_price,
                    'UnitPrice': original_unit_price,
                    'OriginalAmount2': original_unit_price * line.qty,
                    'Amount2': original_unit_price * line.qty,
                    "RowId": line.id,
                    "EinvoiceItemType": 3 if line.is_promotion else 1,
                    "TaxCode": tax_id.code or None,
                    "OriginalAmount3": original_amount3,
                    "Amount3": original_amount3,
                    "CreditAccount3": account.code,
                })
                values.append(value_line)

            order_line_points = order.lines.filtered_domain([('promotion_type', '=', 'point')])
            order_line_cards = order.lines.filtered_domain([('promotion_type', '=', 'card')])
            for order_line in [order_line_points, order_line_cards]:
                tax_ids = order_line.mapped('tax_ids')
                for idx, tax_id in enumerate(tax_ids, start=idx + 1):
                    value_line = copy.copy(value)
                    line = order_line.filtered(lambda f: f.tax_ids in tax_id)
                    product = line.product_id and line.product_id[0]
                    tax_id = line.tax_ids_after_fiscal_position and line.tax_ids_after_fiscal_position[0]
                    account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                    original_unit_price = 0
                    qty = abs(sum(line.mapped('qty')))
                    original_amount3 = abs(sum(line.mapped('price_subtotal'))) * tax_id.amount / 100
                    value_line.update({
                        'CreditAccount2': product.with_company(company).categ_id.property_account_income_categ_id.code or None,
                        'BuiltinOrder': idx,
                        "ItemCode": product.barcode or None,
                        "ItemName": product.name or None,
                        "UnitCode": product.uom_id.code or None,
                        "Quantity9": qty,
                        "ConvertRate9": 1,
                        "Quantity": qty,
                        "OriginalUnitPrice": original_unit_price,
                        'UnitPrice': original_unit_price,
                        "PriceUnit": original_unit_price,
                        'OriginalAmount2': original_unit_price,
                        'Amount2': original_unit_price,
                        "RowId": None,
                        "EinvoiceItemType": 2,
                        "TaxCode": tax_id.code or None,
                        "OriginalAmount3": original_amount3,
                        "Amount3": original_amount3,
                        "CreditAccount3": account.code,
                        "OriginalAmount4": abs(sum(line.mapped('price_subtotal'))),
                        "Amount4": abs(sum(line.mapped('price_subtotal'))),
                        "CreditAccount4": account_receivable,
                        "DebitAccount4": product.with_company(company).categ_id.property_account_income_categ_id.code or None,
                    })
                    values.append(value_line)

        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ đơn bán hàng POS có xuất hóa đơn BKAV", channel="root.Bravo").bravo_execute_query(insert_queries)
        if records:
            self._cr.execute(f"update pos_order set is_bravo_pushed1 = true where id = any (array{records.ids})")

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.env['account.move'].bravo_get_account_doc_sale_columns()
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {}
