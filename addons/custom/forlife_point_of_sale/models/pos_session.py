from odoo import fields, models, api
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_product_ids_by_store(self):
        warehouse_id = self.config_id.picking_type_id.warehouse_id.id
        query = '''
                    WITH sl AS (SELECT id FROM stock_location WHERE warehouse_id = %(warehouse_id)s)
                    SELECT pp.id AS ppid, SUM(sq.quantity) FROM stock_quant sq 
                    JOIN product_product pp ON pp.id = sq.product_id 
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN sl ON sl.id = sq.location_id
                    GROUP BY ppid;
                '''
        self.env.cr.execute(query, {'warehouse_id': warehouse_id})
        data = self.env.cr.fetchall()
        return [id[0] for id in data]

    def _loader_params_product_product(self):
        product_id = self._get_product_ids_by_store()
        res = super(PosSession, self)._loader_params_product_product()
        if product_id and res.get('search_params', False) and res['search_params'].get('domain', False):
            res['search_params']['domain'] = expression.AND(
                [res['search_params']['domain'], ['|', ('id', 'in', product_id), ('detailed_type', '=', 'service')]])
        return res

    def _get_pos_ui_product_product(self, params):
        self = self.with_context(**params['context'])
        if self.config_id.limited_products_loading:
            params['search_params']['limit'] = self.config_id.limited_products_amount
        products = self.env['product.product'].search_read(**params['search_params'])

        self._process_pos_ui_product_product(products)
        return products

    def _get_attributes_by_ptal_id(self):
        return []

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        loaded_data.update({
            'pos_brand_id': self.config_id.store_id.brand_id.id
        })
        return loaded_data
