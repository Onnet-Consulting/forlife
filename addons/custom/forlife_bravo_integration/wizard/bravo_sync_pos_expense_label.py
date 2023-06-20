# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class BravoSyncPosExpenseLabel(models.TransientModel):
    _name = 'bravo.sync.pos.expense.label.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Liquidation Assets wizard'

    def sync(self):
        self.create_and_update_data()
        return True

    @api.model
    def create_and_update_data(self):
        bravo_expense_label_by_code = self.bravo_get_expense_label_data()
        if not bravo_expense_label_by_code:
            return False
        PosExpenseLabel = self.env['pos.expense.label'].sudo()
        odoo_existing_expense_label = PosExpenseLabel.with_context(active_test=False).search(
            [
                ('code', 'in', list(bravo_expense_label_by_code.keys()))
            ])
        odoo_existing_expense_label_by_code = {x.code: x for x in odoo_existing_expense_label}
        odoo_existing_expense_label_codes = list(odoo_existing_expense_label_by_code.keys())
        odoo_new_expense_label_data = []

        for code, bravo_data in bravo_expense_label_by_code.items():
            bravo_expense_name = bravo_data.get("Name", False)
            bravo_expense_push_date = bravo_data.get("PushDate", False)
            bravo_expense_active = bravo_data.get('Active', False)
            if code not in odoo_existing_expense_label_codes:
                odoo_new_expense_label_data.append({
                    "code": code,
                    "name": bravo_expense_name,
                    "bravo_write_date": bravo_expense_push_date,
                    "active": bravo_expense_active
                })
            else:
                odoo_expense = odoo_existing_expense_label_by_code.get(code)
                odoo_expense.write({
                    "name": bravo_expense_name,
                    "bravo_write_date": bravo_expense_push_date,
                    "active": bravo_expense_active
                })
        PosExpenseLabel.create(odoo_new_expense_label_data)
        return True

    @api.model
    def get_expense_label_last_write_date(self):
        """return latest updated label"""
        cr = self.env.cr
        query = """
            SELECT max(bravo_write_date)
            FROM pos_expense_label
        """
        cr.execute(query)
        return cr.fetchone()[0]

    @api.model
    def bravo_get_expense_label_data(self):
        bravo_table = 'B20CashFlow'
        odoo_last_write_date = self.get_expense_label_last_write_date()
        bravo_expense_label_columns = ["Code", "Name", "PushDate", "Active"]
        bravo_expense_label_columns_str = ','.join(bravo_expense_label_columns)
        if not odoo_last_write_date:
            select_query = """
                SELECT %s
                FROM %s
            """ % (bravo_expense_label_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [])])
        else:
            select_query = """
                SELECT %s
                FROM %s
                WHERE PushDate > ?
            """ % (bravo_expense_label_columns_str, bravo_table)
            data = self._execute_many_read([(select_query, [odoo_last_write_date])])

        bravo_expense_label_data_by_code = {}
        for records in data:
            for rec in records:
                rec_value = dict(zip(bravo_expense_label_columns, rec))
                bravo_expense_label_code = rec_value.get("Code")
                if bravo_expense_label_code:
                    bravo_expense_label_data_by_code[bravo_expense_label_code] = rec_value
        return bravo_expense_label_data_by_code
