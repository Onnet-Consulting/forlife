from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    pos_order_id = fields.Many2one('pos.order', readonly=True, string='POS Order')

    def _get_starting_sequence(self):
        self.ensure_one()
        res = super(AccountMove, self)._get_starting_sequence()
        if self.pos_order_ids:
            warehouse_code = self.pos_order_ids[0].config_id.picking_type_id.warehouse_id.code
            return warehouse_code + '/' + res
        if self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id:
            warehouse_code = self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id.code
            return warehouse_code + '/' + res
        return res

    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
        self.ensure_one()
        if self.pos_order_ids or (self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id):
            if self.pos_order_ids:
                warehouse_code = self.pos_order_ids[0].config_id.picking_type_id.warehouse_id.code
            if self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id:
                warehouse_code = self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id.code
            if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
                raise ValidationError(_('%s is not a stored field', self._sequence_field))
            where_string, param = self._get_last_sequence_domain(relaxed)
            if self.id or self.id.origin:
                where_string += " AND id != %(id)s "
                param['id'] = self.id or self.id.origin

            where_string += " AND sequence_prefix like %(warehouse_code)s "
            param['warehouse_code'] = warehouse_code

            query = f"""
                            SELECT {{field}} FROM {self._table}
                            {where_string}
                            AND sequence_prefix = (SELECT sequence_prefix FROM {self._table} {where_string} ORDER BY id DESC LIMIT 1)
                            ORDER BY sequence_number DESC
                            LIMIT 1
                    """
            if lock:
                query = f"""
                        UPDATE {self._table} SET write_date = write_date WHERE id = (
                            {query.format(field='id')}
                        )
                        RETURNING {self._sequence_field};
                        """
            else:
                query = query.format(field=self._sequence_field)

            self.flush_model([self._sequence_field, 'sequence_number', 'sequence_prefix'])
            self.env.cr.execute(query, param)
            return (self.env.cr.fetchone() or [None])[0]
        else:
            return super(AccountMove, self)._get_last_sequence(relaxed, with_prefix, lock)