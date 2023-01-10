from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        all_pos = self.env['pos.config'].search([])
        vals = []
        for r in all_pos:
            vals.append({
                'id': r.id,
                'name': r.name
            })
        loaded_data.update({
            'pos.customize': vals
        })
        return loaded_data

    @api.model
    def _pos_ui_models_to_load(self):
        models_to_load = super(PosSession, self)._pos_ui_models_to_load()
        models_to_load.append('account.bank.statement.line')
        return models_to_load

    def _loader_params_account_bank_statement_line(self):
        return {'search_params': {'domain': [('id','in', self.statement_line_ids.ids)], 'fields': ['name', 'move_id']}}

    def _get_pos_ui_account_bank_statement_line(self, params):
        return self.env['account.bank.statement.line'].search_read(**params['search_params'])

    def create_pos_transfer_journal_entry(self, _type, amount, reason, extras):
        self.ensure_one()
        balance = amount if _type == 'out' else -amount
        move_val = {
            'ref': self.name + ' ' + reason or '',
            'move_type': 'entry',
            'pos_transfer_cash_2office': True,
            'pos_orig_amount': balance,
            'pos_trans_session_id': self.id,
            'narration': self.name + reason or '',
            'currency_id': self.currency_id.id,
            'partner_id': self.config_id.store_id.contact_id.id,
            'company_id': self.company_id.id,
        }
        liquidity_line_vals = {
            'name': _('Transfer POS-Office: %s') % self.name + ' ' + reason or '',
            'partner_id': self.config_id.store_id.contact_id.id,
            'account_id': self.config_id.store_id.default_office_cash_account_id.id,
            'currency_id': self.currency_id.id,
            'debit': balance > 0 and balance or 0.0,
            'credit': balance < 0 and -balance or 0.0,
        }
        # Create the counterpart line values.
        counterpart_line_vals = {
            'name': _('Counterpart Transfer POS-Office: %s') % self.name + ' ' + reason or '',
            'account_id': self.config_id.store_id.account_intermediary_pos.id,
            'partner_id': self.config_id.store_id.contact_id.id,
            'currency_id': self.currency_id.id,
            'debit': -balance if balance < 0.0 else 0.0,
            'credit': balance if balance > 0.0 else 0.0,
        }
        move_val['line_ids'] = [
            (0, 0, liquidity_line_vals),
            (0, 0, counterpart_line_vals)]
        move = self.env['account.move'].create(move_val)
        return move

    def try_cash_in_out(self, _type, amount, reason, extras):
        res = super(PosSession, self).try_cash_in_out(_type, amount, reason, extras)
        sign_2 = -1 if _type == 'in' else 1
        sessions = self.filtered('cash_journal_id')
        if extras['reference'] and extras['shop']:
            payment = self.env['account.bank.statement.line'].create([
                {
                    'pos_session_id': extras['shop'],
                    'journal_id': session.cash_journal_id.id,
                    'amount': sign_2 * amount,
                    'date': fields.Date.context_today(self),
                    'payment_ref': '-'.join([session.name, extras['translatedType'], reason]),
                }
                for session in sessions
            ])
            bank_statement_lin = self.env['account.bank.statement.line'].sudo().search([('id','=', int(extras['reference']))])
            try:
                payment.move_id.write({
                    'name': 'Ref- {}'.format(bank_statement_lin.name)
                })
            except Exception as e:
                self.message_post(body=e)
        if extras['type_tranfer'] == 1:
            if _type == 'in':
                raise UserError(_('Amount transferred to company must be a negative number and transfer type \'out\''))
            for session in sessions:
                session.create_pos_transfer_journal_entry(_type, amount, reason, extras)
        return res
