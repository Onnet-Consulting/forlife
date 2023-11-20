# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import copy


class BravoSummaryAdjustedInvoiceSoNhanh(models.Model):
    _name = 'summary.adjusted.invoice.so.nhanh'
    _inherit = ['summary.adjusted.invoice.so.nhanh', 'bravo.model.insert.action']
    _bravo_table = 'B30AccDocSalesAdjust'

    is_bravo_pushed = fields.Boolean('Bravo pushed', default=False, copy=False)

    @api.model
    def sync_bravo_adjusted_invoice_so_nhanh(self):
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
                "DocCode": "HC",
                "FormNo": line.invoice_serial or None,
                "DocNo": line.invoice_no or line.code or None,
                "DocDate": line.invoice_date or None,
                "CurrencyCode": company.currency_id.name or None,
                "ExchangeRate": exchange_rate,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "TaxRegNo": partner.vat or None,
                "Description": f"Hóa đơn điểu chỉnh bán hàng Online {line.invoice_date.strftime('%d/%m/%Y') if line.invoice_date else ''}",
                "IsTransfer": 1 if line.invoice_no else 0,
                "CreditAccount2": account_receivable,
                "DueDate": line.invoice_date or None,
                "DeptCode": partner.property_account_cost_center_id.code or None,
                "EInvoiceTransType": 'adjustDecrease',
                "EInvoiceOriginNo": (line.source_invoice and (line.source_invoice.invoice_no or line.source_invoice.code)) or None,
                "OriginFormNo": line.source_invoice and line.source_invoice.invoice_no or None,
            }
            for idx, detail in enumerate(line.line_ids, start=1):
                value_line = copy.copy(value)
                convert_rate = 1
                value_line.update({
                    'BuiltinOrder': idx,
                    "ItemCode": detail.product_id.barcode or None,
                    "ItemName": detail.product_id.name or None,
                    "UnitCode": detail.product_id.uom_id.code or None,
                    "DebitAccount2": detail.with_company(company).product_id.categ_id.x_property_account_return_id.code or None,
                    "Quantity9": abs(detail.quantity),
                    "ConvertRate9": convert_rate,
                    "Quantity": abs(detail.quantity) * convert_rate,
                    "OriginalUnitPrice": abs(detail.price_unit),
                    'UnitPrice': abs(detail.price_unit) * exchange_rate,
                    "PriceUnit": abs(detail.price_unit),
                    'OriginalAmount2': abs(detail.price_subtotal),
                    'Amount2': abs(detail.price_subtotal) * exchange_rate,
                    "RowId": detail.id,
                    "EinvoiceItemType": 3 if detail.x_free_good else 1,
                })
                tax_id = detail.tax_ids
                if tax_id:
                    tax_line = tax_id and tax_id[0]
                    account = tax_id.invoice_repartition_line_ids.account_id and tax_id.invoice_repartition_line_ids.account_id[0]
                    value_line.update({
                        "TaxCode": tax_line.code,
                        "OriginalAmount3": detail.tax_amount,
                        "Amount3": detail.tax_amount * exchange_rate,
                        "CreditAccount3": account_receivable,
                        "DebitAccount3": account.code,
                    })
                values.append(value_line)
        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ hóa đơn điều chỉnh tổng hợp SO nhanh", channel="root.Bravo").bravo_execute_query(insert_queries)
        if results:
            self._cr.execute(f"update summary_adjusted_invoice_so_nhanh set is_bravo_pushed = true where id = any (array{results.ids})")

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.env['account.move'].bravo_get_account_doc_sale_adjust_columns()
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {'PushDate': self and self[0].create_date or "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}
