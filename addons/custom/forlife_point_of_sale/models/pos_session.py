from odoo import fields, models, api
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_product_ids_by_store(self):
        location_id = self.config_id.picking_type_id.default_location_src_id.id
        query = '''
                    SELECT pp.id AS ppid, sq.quantity FROM stock_quant sq 
                    RIGHT JOIN product_product pp ON pp.id = sq.product_id 
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE location_id = %(location_id)s 
                    AND sq.quantity > 0 or pt.detailed_type = 'service'
                '''
        self.env.cr.execute(query, {'location_id': location_id})
        data = self.env.cr.fetchall()
        return [id[0] for id in data]

    def _loader_params_product_product(self):
        values = super(PosSession, self)._loader_params_product_product()
        values['search_params']['fields'].append('full_attrs_desc')
        return values

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
        pos_brand = self.config_id.store_id.brand_id
        pos_brand_info = {"code": pos_brand.code, "id": pos_brand.id}
        loaded_data.update({
            'pos_brand_info': pos_brand_info
        })
        return loaded_data

    def _process_pos_ui_product_product(self, products):
        product_ids = set(self._get_product_ids_by_store())
        new_products = []
        for product in products:
            if product.get('id') in product_ids:
                new_products.append(product)
        products[:] = new_products
        return super(PosSession, self)._process_pos_ui_product_product(products)
