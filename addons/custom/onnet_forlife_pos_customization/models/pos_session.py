from odoo import api, fields, models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        all_pos = self.env['pos.config'].search([])
        vals = []
        for r in all_pos:
            val.append({
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

    def _loader_params_pos_session(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.id)],
                'fields': [
                    'id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at', 'sequence_number',
                    'payment_method_ids', 'state', 'update_stock_at_closing', 'cash_register_balance_start', 'statement_line_ids'
                ],
            },
        }


    def _loader_params_account_bank_statement_line(self):
        return {'search_params': {'domain': [('id','in', self.statement_line_ids.ids)], 'fields': ['name', 'move_id']}}

    def _get_pos_ui_account_bank_statement_line(self, params):
        return self.env['account.bank.statement.line'].search_read(**params['search_params'])
