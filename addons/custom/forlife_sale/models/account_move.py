from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if vals.get('narration'):
            self.update_narration()
        return res

    def update_narration(self):

        """ update note, narration of parent Journal Entry """

        sql = f"""
                update account_move
                set narration = %s
                where (ref = '{self.name}' or name = '{self.ref}' or ref ='{self.ref}')
                and name !=''and ref !=''
                and state != 'draft'
            """
        self._cr.execute(sql, (self.narration,))
        if self.stock_move_id:
            sql = f"""
                update stock_picking
                set note = %s
                from (select picking_id from stock_move
                                        where id = {self.stock_move_id.id}) as A
                where stock_picking.id = A.picking_id
            """
            self._cr.execute(sql, (self.narration,))
