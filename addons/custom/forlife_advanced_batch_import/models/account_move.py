from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        super(AccountMove, self)._compute_name()
        for rec in self:
            if rec.state == 'posted' and rec.name != '/':
                rec.name = rec.sequence_prefix + str(rec.id)