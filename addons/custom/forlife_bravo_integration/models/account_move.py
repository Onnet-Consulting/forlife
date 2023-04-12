# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'bravo.model.insert.action']

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        posted_moves = self.filtered(lambda m: m.state == 'posted')
        insert_queries = posted_moves.bravo_get_insert_sql()
        self.env[self._name].sudo().with_delay().bravo_insert(insert_queries)
        return res

    @api.model
    def bravo_get_table(self):
        return 'B30AccDocSales'

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def get_sale_bill_data(self):
        move_lines = self.mapped('invoice_line_ids').filtered(lambda ml: ml.sale_line_ids)
        bravo_column_names = []
        moves_data=  []
        for idx, line in enumerate(move_lines, start=1):
            move = line.move_id
            move_partner = move.partner_id
            bravo_data = {
                "CompanyCode": move.company_id.code,
                "Stt": line.id,
                "DocCode": "H2",
                "DocDate": move.invoice_date,
                "CurrencyCode": move.currency_id.name,
                "ExchangeRate": move.currency_id.rate,
                "CustomerCode": move_partner.ref,
                "CustomerName": move_partner.name,
                "Address": move_partner.contact_address_complete,
                "TaxRegNo": move_partner.vat,
                "EmployeeCode": move.invoice_user_id.employee_id.code,
            }

    def bravo_get_insert_values(self):
        return [],[]

