from odoo import fields, models, api
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        product_combos = self.env['product.combo'].sudo().search([('state', '=', 'in_progress')])
        product_combo_lines = []
        for rec in product_combos:
            product_combolines = self.env['product.combo.line'].sudo().search([('combo_id', '=', rec.id), ('state', '=', 'in_progress')])
            combo_ids = [{
                'product_id': cpl.product_id.id,
                'product_name': cpl.product_id.name,
                'quantity': cpl.max_quantity,
            } for cpl in product_combolines]

            product_combo_list = {
                'id': rec.id,
                'code': rec.code,
                'from_date': rec.from_date,
                'to_date': rec.to_date,
                'size_deviation_allowed': rec.size_deviation_allowed,
                'color_deviation_allowed': rec.color_deviation_allowed,
                'product_combolines': combo_ids,
            }
            product_combo_lines.append(product_combo_list)

        # product_combos = [{
        #     'id': r.id,
        #     'code': r.code,
        #     'from_date': r.from_date,
        #     'to_date': r.to_date,
        #     'size_deviation_allowed': r.size_deviation_allowed,
        #     'color_deviation_allowed': r.color_deviation_allowed
        # } for r in product_combos]

        loaded_data.update({
            'product_combo': product_combo_lines,
        })
        return loaded_data
    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('combo_id')

        return result