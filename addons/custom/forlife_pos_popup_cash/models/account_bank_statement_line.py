from odoo import api, fields, models

class AccountBank(models.Model):
    _inherit = 'account.bank.statement.line'

    from_store_tranfer = fields.Many2one('pos.config', 'From POS?', readonly=True)
    to_store_tranfer = fields.Many2one('pos.config', 'To POS?', readonly=True)
    is_reference = fields.Boolean('Is Reference Tranfer?')

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        res = super(AccountBank, self)._prepare_move_line_default_vals(counterpart_account_id)
        if counterpart_account_id is None and self.to_store_tranfer or self.from_store_tranfer or self.is_reference:
            res[1]['account_id'] = self.pos_session_id.config_id.store_id.account_intermediary_pos.id
            res[1]['partner_id'] = self.pos_session_id.config_id.store_id.contact_id.id
        return res
