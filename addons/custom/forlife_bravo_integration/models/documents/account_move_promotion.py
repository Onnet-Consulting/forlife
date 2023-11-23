# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime


class AccountMovePromotion(models.Model):
    _inherit = 'account.move.promotion'

    is_bravo_pushed = fields.Boolean('Bravo pushed', default=False, copy=False)


class BravoSyncAccountMovePromotionShippingFee(models.AbstractModel):
    _name = 'sync.account.move.promotion.shipping.fee'
    _inherit = 'bravo.model.insert.action'
    _bravo_table = "B30AccDocPurchase"

    def sync_bravo_promotion_shipping_fee(self):
        self._cr.execute(f"""
            with am_promotion as (select id, move_id
                                  from account_move_promotion
                                  where is_bravo_pushed = false
                                    and promotion_type = 'nhanh_shipping_fee'),
                 invoice_origins as (select distinct invoice_origin
                                     from account_move
                                     where id in (select move_id from am_promotion)
                                       and invoice_origin notnull),
                 account_move_in_sale_online as (select id
                                                 from account_move
                                                 where id in (select distinct move_id from am_promotion)
                                                   and invoice_origin
                                                     in (select name
                                                         from sale_order
                                                         where x_sale_chanel = 'online'
                                                           and company_id = {self.env.company.id}
                                                           and name in (select * from invoice_origins))),
                 list_id_final as (select amp.id, to_char(am.date + interval '7 h', 'YYYY-MM-DD_YY') as date
                                   from account_move_promotion amp
                                            join account_move am on amp.move_id = am.id
                                   where amp.move_id in (select id from account_move_in_sale_online)
                                     and amp.id in (select distinct id from am_promotion)),
                 update_data as (update account_move_promotion set is_bravo_pushed = true where id in (select id from list_id_final))
            select date, json_agg(id) as list_id
            from list_id_final
            group by date
        """)
        record_by_date = self._cr.fetchall()
        prefix_name_by_company = {
            '1100': '9511',
            '1200': '9512',
            '1300': '9513',
            '1400': '9514',
        }
        values = []
        for key, list_id in record_by_date:
            _time = key.split('_')
            records = self.env['account.move.promotion'].browse(list_id)
            stt_prefix = f"{prefix_name_by_company.get(self.env.company.code)}{_time[1]}"
            stt_sequence = self.env['ir.sequence'].search([('code', '=', stt_prefix)], limit=1)
            if not stt_sequence:
                vals = {
                    'name': 'Chi phí vận chuyển ước tính trên đơn NHANH: ' + stt_prefix,
                    'code': stt_prefix,
                    'company_id': None,
                    'prefix': stt_prefix,
                    'padding': 8,
                    'number_increment': 1,
                    'number_next_actual': 1
                }
                stt_sequence = self.env['ir.sequence'].create(vals)
            _stt = stt_sequence._next()
            partner = records.move_id.partner_id and records.move_id.partner_id[0]
            account_payable_code = partner.property_account_payable_id.code or None
            product = records.product_id and records.product_id[0]
            credit_account = records.account_id and records.account_id[0]
            tax = records.tax_id and records.tax_id[0]
            total_value = abs(sum(records.mapped('value')))
            price_unit = total_value / (1 + tax.amount / 100)
            debit_account3 = tax.invoice_repartition_line_ids.account_id and tax.invoice_repartition_line_ids.account_id[0]
            analytic_account_code = records.analytic_account_id and records.analytic_account_id[0].code or partner.sudo().property_account_cost_center_id.code

            values.append({
                "CompanyCode": self.env.company.code or None,
                "Stt": _stt,
                "DocCode": 'NM',
                "DocNo": _stt,
                "DocDate": _time[0],
                "CurrencyCode": self.env.company.currency_id.name or None,
                "ExchangeRate": 1,
                "CustomerCode": partner.ref or None,
                "CustomerName": partner.name or None,
                "Address": partner.contact_address_complete or None,
                "TaxRegName": partner.name or None,
                "TaxRegNo": partner.vat or None,
                "Description": f"Chi phí vận chuyển đơn hàng NHANH {datetime.strptime(_time[0], '%Y-%m-%d').strftime('%d/%m/%Y')}",
                "EmployeeCode": None,
                "IsTransfer": 0,
                "CreditAccount": account_payable_code,
                "PushDate": _time[0],
                "DueDate": _time[0],
                "IsCompany": 3,
                "BuiltinOrder": 1,
                "ItemCode": product.barcode or None,
                "ItemName": product.name or None,
                "UnitPurCode": product.uom_id.code or None,
                "DebitAccount": credit_account.code or None,
                "Quantity9": 1,
                "ConvertRate9": 1,
                "Quantity": 1,
                "PriceUnit": price_unit,
                "OriginalPriceUnit": price_unit,
                "Discount": 0,
                "OriginalDiscount": 0,
                "OriginalUnitCost": price_unit,
                "UnitCost": price_unit,
                "OriginalAmount": price_unit,
                "Amount": price_unit,
                "TaxCode": tax.code or None,
                "OriginalAmount3": price_unit * tax.amount / 100,
                "Amount3": price_unit * tax.amount / 100,
                "DebitAccount3": debit_account3.code or None,
                "CreditAccount3": debit_account3 and account_payable_code or None,
                "RowId": None,
                "DeptCode": analytic_account_code or None,
                "ExpenseCatgCode": '7710501',
            })

        if values:
            insert_queries = self.bravo_get_insert_sql(data=values)
            if insert_queries:
                self.sudo().with_delay(description=f"Bravo: đồng bộ tổng hợp chi phí vận chuyển ước tính trên đơn NHANH", channel="root.Bravo").bravo_execute_query(insert_queries)

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        column_names = self.bravo_get_promotion_shipping_fee()
        values = kwargs.get('data')
        return column_names, values

    @api.model
    def bravo_get_promotion_shipping_fee(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "TaxRegName", "TaxRegNo", "EmployeeCode", "IsTransfer",
            "CreditAccount", "PushDate", "DueDate", "IsCompany", "BuiltinOrder", "ItemCode", "ItemName",
            "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9", "Quantity", "PriceUnit", "OriginalPriceUnit",
            "Discount", "OriginalDiscount", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "TaxCode",
            "OriginalAmount3", "Amount3", "DebitAccount3", "CreditAccount3", "RowId", "DeptCode", "ExpenseCatgCode"
        ]

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        return {}
