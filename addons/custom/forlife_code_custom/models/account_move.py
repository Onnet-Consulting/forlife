from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_declare_code(self):
        declare_code_id = self.env['declare.code']._get_declare_code('', self.company_id.id, self.journal_id.id)
        return declare_code_id
    

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
        for move in self:
            
            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                if not move.posted_before and not move._sequence_matches_date():
                    if move._get_last_sequence(lock=False):
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        move.name = False
                        continue
                else:
                    if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence(lock=False):
                        # The move either
                        # - has a name and was posted before, or
                        # - doesn't have a name, but is not the first in the period
                        # so we don't recompute the name
                        continue
            if move.date and (not move_has_name or not move._sequence_matches_date()):
                declare_code_id = move._get_declare_code()
                if not declare_code_id:
                    move._set_next_sequence()
                else:
                    move.name = declare_code_id.genarate_code('account_move','name')

        self.filtered(lambda m: not m.name and not move.quick_edit_mode).name = '/'
        self._inverse_name()

