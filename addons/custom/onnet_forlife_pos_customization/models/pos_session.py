from odoo import api, fields, models

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
        return res