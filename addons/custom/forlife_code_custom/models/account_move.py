from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_declare_code(self):
        declare_code_id = self.env['declare.code']._get_declare_code('', self.company_id.id, self.journal_id.id)
        return declare_code_id
    

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
        highest_name = self[0]._get_last_sequence(lock=False) if self else False
        sequence = 0
        for move in self:
            store_code = '0000'
            if move.pos_order_ids:
                store_code = move.pos_order_ids[0].config_id.picking_type_id.warehouse_id.code
            if move.pos_order_id:
                store_code = move.pos_order_id.config_id.picking_type_id.warehouse_id.code
            if move.stock_valuation_layer_ids and move.stock_valuation_layer_ids[0].stock_move_id.picking_id and \
                    move.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id:
                store_code = move.stock_valuation_layer_ids[
                    0].stock_move_id.picking_id.picking_type_id.warehouse_id.code
            check_origin_entry = False
            if move.pos_order_id or move.pos_order_ids or (move.stock_valuation_layer_ids and move.stock_valuation_layer_ids[0].stock_move_id.picking_id and move.stock_valuation_layer_ids[0].stock_move_id.picking_id.picking_type_id.warehouse_id):
                check_origin_entry = True
            if not highest_name and move == self[0] and not move.posted_before and move.date and (not move.name or move.name == '/'):
                # In the form view, we need to compute a default sequence so that the user can edit
                # it. We only check the first move as an approximation (enough for new in form view)
                declare_code_id = move._get_declare_code()
                if not declare_code_id or check_origin_entry:
                    move._set_next_sequence()
                else:
                    move.name = declare_code_id.genarate_code(move.company_id.id,'account.move','name',sequence,store_code)
                    sequence += 1
            elif move.quick_edit_mode and not move.posted_before:
                # We always suggest the next sequence as the default name of the new move
                declare_code_id = move._get_declare_code()
                if not declare_code_id or check_origin_entry:
                    move._set_next_sequence()
                else:
                    move.name = declare_code_id.genarate_code(move.company_id.id,'account.move','name',sequence,store_code)
                    sequence += 1
            elif (move.name and move.name != '/') or move.state != 'posted':
                try:
                    move._constrains_date_sequence()
                    # The name matches the date: we don't recompute
                except ValidationError:
                    # Has never been posted and the name doesn't match the date: recompute it
                    declare_code_id = move._get_declare_code()
                    if not declare_code_id or check_origin_entry:
                        move._set_next_sequence()
                    else:
                        move.name = declare_code_id.genarate_code(move.company_id.id,'account.move','name',sequence,store_code)
                        sequence += 1
            else:
                # The name is not set yet and it is posted
                declare_code_id = move._get_declare_code()
                if not declare_code_id or check_origin_entry:
                    move._set_next_sequence()
                else:
                    move.name = declare_code_id.genarate_code(move.company_id.id,'account.move','name',sequence,store_code)
                    sequence += 1

        self.filtered(lambda m: not m.name).name = '/'

