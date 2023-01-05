from odoo import api, fields, models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = {}
        self = self.with_context(loaded_data=loaded_data)
        for model in self._pos_ui_models_to_load():
            loaded_data[model] = self._load_model(model)
        self._pos_data_process(loaded_data)
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
        models_to_load = [
            'res.company',
            'decimal.precision',
            'uom.uom',
            'res.country.state',
            'res.country',
            'res.lang',
            'account.tax',
            'pos.session',
            'pos.config',
            'pos.bill',
            'res.partner',
            'stock.picking.type',
            'res.users',
            'product.pricelist',
            'res.currency',
            'pos.category',
            'product.product',
            'product.packaging',
            'account.cash.rounding',
            'pos.payment.method',
            'account.fiscal.position',
            'account.bank.statement.line'
        ]

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
