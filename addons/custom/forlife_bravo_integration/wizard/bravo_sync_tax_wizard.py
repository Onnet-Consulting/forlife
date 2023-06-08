# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BravoSyncTaxWizard(models.TransientModel):
    _name = 'bravo.sync.tax.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Taxes wizard'

    def sync(self):
        companies = self.env['res.company'].search([('code', '!=', False)])
        bravo_taxes = self.get_bravo_taxes()
        for company in companies:
            self = self.with_company(company).sudo()
            self.update_odoo_taxes_by_company(bravo_taxes)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def get_bravo_taxes(self):
        bravo_table = 'B20Tax'
        bravo_columns = ['Code', 'Rate', 'Type', 'Account']
        bravo_columns_str = ','.join(bravo_columns)
        select_query = """
            SELECT %s
            FROM %s
        """ % (bravo_columns_str, bravo_table)
        data = self._execute_many_read([(select_query, [])])
        bravo_taxes = []
        res = {1: {}, 2: {}}  # tax value by type and code
        for records in data:
            for rec in records:
                rec_value = dict(zip(bravo_columns, rec))
                bravo_taxes.append(rec_value)

        for tax_value in bravo_taxes:
            tax_type = tax_value['Type']
            tax_rate = tax_value['Rate']
            if tax_type not in res:
                continue
            res[tax_type][tax_rate] = {
                'code': tax_value['Code'],
                'account': tax_value['Account']
            }

        return res

    def get_odoo_taxes_by_company(self):
        taxes = self.env['account.tax'].search([('type_tax_use', '!=', 'none'), ('company_id', '=', self.env.company.id)])
        res = []
        for tax in taxes:
            tax_value = {
                'record': tax,
                'amount': tax.amount,
                'type': 1 if tax.type_tax_use == 'purchase' else 2
            }
            res.append(tax_value)
        return res

    def update_odoo_taxes_by_company(self, bravo_taxes):
        odoo_taxes = self.get_odoo_taxes_by_company()
        bravo_account_codes = []
        for value in bravo_taxes.values():
            for detail_value in value.values():
                bravo_account_codes.append(detail_value['account'])
        odoo_accounts = self.env['account.account'].search([('code', 'in', bravo_account_codes), ('company_id', '=', self.env.company.id)])
        odoo_account_id_by_code = {}
        for oac in odoo_accounts:
            odoo_account_id_by_code[oac.code] = oac.id

        missing_accounts = set(bravo_account_codes) - set(odoo_account_id_by_code.keys())
        if missing_accounts:
            raise ValidationError(_('Missing accounts code in company %s: %r') % (self.env.company.name, missing_accounts))

        for tax_value in odoo_taxes:
            odoo_type = tax_value['type']
            odoo_amount = tax_value['amount']

            if not bravo_taxes.get(odoo_type) or not bravo_taxes.get(odoo_type).get(odoo_amount):
                continue
            odoo_tax_record = tax_value['record']
            bravo_tax_value = bravo_taxes[odoo_type][odoo_amount]
            bravo_code = bravo_tax_value['code']
            bravo_account_code = bravo_tax_value['account']
            odoo_account_id = odoo_account_id_by_code[bravo_account_code]
            odoo_tax_record.write({
                'code': bravo_code,
            })
            odoo_tax_record.invoice_repartition_line_ids.filtered(lambda rep: rep.repartition_type == 'tax').write(
                {'account_id': odoo_account_id})
            odoo_tax_record.refund_repartition_line_ids.filtered(lambda rep: rep.repartition_type == 'tax').write(
                {'account_id': odoo_account_id})
        return True

