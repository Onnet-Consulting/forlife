from odoo import fields, models, api
from odoo.osv import expression
from datetime import datetime, time

class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        now = datetime.now()
        product_combos = self.env['product.combo'].sudo().search([('state', '=', 'in_progress'), ('to_date', '>=', now)])
        product_combo_lines = []
        for rec in product_combos:
            product_combolines = self.env['product.combo.line'].sudo().search([('combo_id', '=', rec.id), ('state', '=', 'in_progress')])
            combo_ids = [{
                'product_id': cpl.product_id.id,
                'product_name': cpl.product_id.name,
                'sku_code': cpl.product_id.sku_code,
                'quantity': cpl.max_quantity,
            } for cpl in product_combolines]

            product_combo_list = {
                'id': rec.id,
                'code': rec.code,
                'from_date': rec.from_date,
                'to_date': rec.to_date,
                'size_attribute_id': rec.size_attribute_id.id,
                'color_attribute_id': rec.color_attribute_id.id,
                'product_combolines': combo_ids,
            }
            product_combo_lines.append(product_combo_list)

        loaded_data.update({
            'product_combo': product_combo_lines,
        })
        return loaded_data
    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        # result['search_params']['fields'].append('attribute_ids')
        result['search_params']['fields'].append('combo_id')

        return result
