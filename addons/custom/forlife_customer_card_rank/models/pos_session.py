from odoo import api, fields, models, _
import json
import base64


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        res = super(PosSession, self)._loader_params_res_partner()
        res['search_params']['fields'] += ['card_rank_by_brand']
        return res

    def _pos_data_process(self, loaded_data):
        super(PosSession, self)._pos_data_process(loaded_data)
        loaded_data['card_rank_program_by_rank_id'] = {p['card_rank_id'][0]: {
            'id': p['id'],
            'name': p['name'],
            'from_date': p['from_date'],
            'to_date': p['to_date'],
            'card_rank_id': p['card_rank_id'][0],
            'card_rank_name': p['card_rank_id'][1],
            'on_original_price': p['original_price'],
            'extra_discount': [{'from': disc[1], 'to': disc[2], 'disc': disc[0]}
                               for disc in sorted([[p['value1'], p['apply_value_from_1'], p['apply_value_to_1']],
                                                   [p['value2'], p['apply_value_from_2'], p['apply_value_to_2']],
                                                   [p['value3'], p['apply_value_from_3'], p['apply_value_to_3']]],
                                                  key=lambda r: r[0])[::-1] if disc[0] > 0],
            'customer_not_apply': json.loads(base64.b64decode(p['customer_not_apply']).decode()) if p['customer_not_apply'] else [],
        } for p in loaded_data['member.card']}
        loaded_data.pop('member.card')
        if 'pos.branch' not in loaded_data:
            brand = self.config_id.store_id.brand_id
            loaded_data['pos.branch'] = [{'id': brand.id, 'name': brand.name}]

    @api.model
    def _pos_ui_models_to_load(self):
        models_to_load = super(PosSession, self)._pos_ui_models_to_load()
        if 'member.card' not in models_to_load:
            models_to_load.append('member.card')
        return models_to_load

    def _loader_params_member_card(self):
        return {
            'search_params': {
                'domain': [
                    ('brand_id', '=', self.config_id.store_id.brand_id.id),
                    ('to_date', '>=', fields.Date.today()),
                    ('from_date', '<=', fields.Date.today()),
                ],
                'fields': [
                    'id', 'name', 'from_date', 'to_date', 'card_rank_id', 'original_price', 'apply_value_from_1', 'apply_value_to_1', 'value1',
                    'apply_value_from_2', 'apply_value_to_2', 'value2', 'apply_value_from_3', 'apply_value_to_3', 'value3', 'customer_not_apply',
                ],
            }
        }

    def _get_pos_ui_member_card(self, params):
        return self.env['member.card'].search_read(**params['search_params'])

    def _loader_params_promotion_program(self):
        result = super()._loader_params_promotion_program()
        result['search_params']['fields'] += ['skip_card_rank']
        return result
