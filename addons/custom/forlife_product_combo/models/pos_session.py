from odoo import fields, models, api
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        product_combos = self.env['product.combo'].sudo().search([('state', '=', 'in_progress')])

        product_combos = [{
            'id': r.id,
            'code': r.code,
            'from_date': r.from_date,
            'to_date': r.to_date,
            'size_deviation_allowed': r.size_deviation_allowed,
            'color_deviation_allowed': r.color_deviation_allowed
        } for r in product_combos]

        loaded_data.update({
            'product_combo': product_combos,
        })
        return loaded_data
    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('combo_id')

        return result