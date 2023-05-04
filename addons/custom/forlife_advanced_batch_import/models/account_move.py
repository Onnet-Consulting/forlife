from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        # super(AccountMove, self)._compute_name()
        if self.env.context.get('job_uuid', False):
            for rec in self:
                if rec.state == 'posted' and rec.name == '/':
                    rec.name = rec.get_prefix_name() + str(rec.id)
        else:
            super(AccountMove, self)._compute_name()
    def get_prefix_name(self):
        self.ensure_one()
        is_payment = self.payment_id or self._context.get('is_payment')
        if self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s/%04d/" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and is_payment:
            starting_sequence = "P" + starting_sequence

        return starting_sequence