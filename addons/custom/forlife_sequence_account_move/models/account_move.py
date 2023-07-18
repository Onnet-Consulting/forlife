from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

class AccountMove(models.Model):
    _inherit = "account.move"

    pos_order_id = fields.Many2one('pos.order', readonly=True, string='POS Order')

    def _get_starting_sequence(self):
        self.ensure_one()
        res = super(AccountMove, self)._get_starting_sequence()
        if self.pos_order_ids:
            warehouse_code = self.pos_order_ids[0].config_id.picking_type_id.warehouse_id.code
            return warehouse_code + '/' + res
        if self.pos_order_id:
            warehouse_code = self.pos_order_id.config_id.picking_type_id.warehouse_id.code
            return warehouse_code + '/' + res
        if self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id and self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id:
            warehouse_code = self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id.code
            return warehouse_code + '/' + res
        return res

    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
        self.ensure_one()
        if self.pos_order_id or self.pos_order_ids or (self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id and self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id):
            if self.pos_order_ids:
                warehouse_code = self.pos_order_ids[0].config_id.picking_type_id.warehouse_id.code
            if self.pos_order_id:
                warehouse_code = self.pos_order_id.config_id.picking_type_id.warehouse_id.code
            if self.stock_valuation_layer_ids and self.stock_valuation_layer_ids[0].stock_move_id.picking_id:
                warehouse_code = self.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id.code
            if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
                raise ValidationError(_('%s is not a stored field', self._sequence_field))
            where_string, param = self._get_last_sequence_domain(relaxed)
            if self.id or self.id.origin:
                where_string += " AND id != %(id)s "
                param['id'] = self.id or self.id.origin

            where_string += " AND sequence_prefix like %(warehouse_code)s "
            param['warehouse_code'] = warehouse_code + '/%'

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

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if not self.date or not self.journal_id:
            return "WHERE FALSE", {}
        where_string = "WHERE journal_id = %(journal_id)s AND name != '/'"
        param = {'journal_id': self.journal_id.id}
        is_payment = self.payment_id or self._context.get('is_payment')

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
            if self.journal_id.payment_sequence:
                domain += [('payment_id', '!=' if is_payment else '=', False)]
            reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
            if sequence_number_reset == 'year':
                where_string += " AND date >= date_trunc('year', %(date)s) AND date < date_trunc('year', %(date)s + interval '1 year') "
                param['date'] = self.date
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'month':
                where_string += " AND date >= date_trunc('month', %(date)s) AND date < date_trunc('month', %(date)s + interval '1 month') "
                param['date'] = self.date
            else:
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
        elif self.journal_id.payment_sequence:
            if is_payment:
                where_string += " AND payment_id IS NOT NULL "
            else:
                where_string += " AND payment_id IS NULL "

        return where_string, param