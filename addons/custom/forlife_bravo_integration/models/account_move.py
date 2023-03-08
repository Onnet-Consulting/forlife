# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField, BravoCharField, BravoDatetimeField, BravoDateField, \
    BravoMany2oneField, BravoIntegerField, BravoDecimalField
from odoo.exceptions import ValidationError

DEFAULT_VALUE = {
    'PushDate': 'GETUTCDATE()'
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        # FIXME: move this method to job queue
        self.insert_to_bravo()
        return res

    def insert_to_bravo(self):
        posted_moves = self.filtered(lambda move: move.state == 'posted')
        purchase_picking_moves = posted_moves.filtered(lambda move: move.stock_move_id.purchase_line_id)
        self.env['bravo.account.move.purchase.picking'].create(
            [{'move_id': move.id} for move in purchase_picking_moves])
        posted_moves = posted_moves - purchase_picking_moves
        # TODO: add other type of account.move to bravo
        return True

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        return res


class BravoAccountMove(models.AbstractModel):
    _name = 'bravo.account.move.model'
    _inherit = ['mssql.server']

    move_id = fields.Many2one('account.move', required=True)

    def get_bravo_insert_sql(self):
        self.ensure_one()
        column_names, values = self.get_bravo_insert_values()
        if not values:
            return False
        queries = []
        insert_table = self._bravo_table
        params = []
        insert_column_names = column_names.copy()
        single_record_values_placeholder = ['?'] * len(column_names)

        for rec_value in values:
            for fname in column_names:
                params.append(rec_value.get(fname))

        for fname, fvalue in DEFAULT_VALUE.items():
            insert_column_names.append(fname)
            single_record_values_placeholder.append(str(fvalue))

        single_record_values_placeholder = "(" + ','.join(single_record_values_placeholder) + ")"
        insert_column_names = "(" + ','.join(insert_column_names) + ")"

        # LIMITATION params per request is 2100 -> so 2000 params per request is a reasonable number
        num_param_per_row = len(column_names)
        num_row_per_request = 2000 // num_param_per_row
        offset = 0
        while True:
            sub_params = params[offset: num_row_per_request * num_param_per_row + offset]
            actual_num_row = len(sub_params) // num_param_per_row
            if actual_num_row <= 0:
                break
            insert_values_placholder = ','.join([single_record_values_placeholder] * actual_num_row)
            sub_query = f"""
                    INSERT INTO {insert_table} 
                    {insert_column_names}
                    VALUES {insert_values_placholder}
                    """
            queries.append((sub_query, sub_params))
            offset += num_row_per_request * num_param_per_row

        return queries

    def insert_into_bravo_db(self):
        # FIXME: move to queue job
        for record in self:
            queries = record.get_bravo_insert_sql()
            if queries:
                record._execute_many(queries)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super(BravoAccountMove, self).create(vals_list)
        res.insert_into_bravo_db()
        return res


class BravoAccountMovePurchase(models.TransientModel):
    _name = 'bravo.account.move.purchase.picking'
    _inherit = ['bravo.account.move.model']
    _bravo_table = 'B30AccDocPurchase'

    def get_bravo_insert_values(self):
        self.ensure_one()
        move_id = self.move_id
        partner = self.move_id.partner_id

        header_data = {
            "BranchCode": move_id.company_id.code,
            "Stt": move_id.id,
            "DocNo": move_id.stock_move_id.picking_id.name,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Description": move_id.narration
        }
        field_names = list(header_data.keys())
        field_names.extend(['RowId', 'Amount', 'DebitAccount', 'CreditAccount'])
        line_data = []
        for line in move_id.line_ids:
            line_value = {
                "RowId": line.id,
                "Amount": line.debit or line.credit,
            }
            if line.debit:
                line_value.update({
                    'DebitAccount': line.account_id.code
                })
            else:
                line_value.update({
                    'CreditAccount': line.account_id.code
                })
            line_value.update(header_data)
            line_data.append(line_value)

        return field_names, line_data
