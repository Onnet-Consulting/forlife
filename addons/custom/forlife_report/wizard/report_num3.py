# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ReportNum3(models.TransientModel):
    _name = 'report.num3'
    _inherit = 'report.base'
    _description = 'Report stock in time range by warehouse'

    from_date = fields.Date(string='From date')
    to_date = fields.Date(string='To date', required=True)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')

    def view_report(self):
        self.ensure_one()
        action = self.env.ref('forlife_report.report_num_3_client_action').read()[0]
        return action

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang

        where_query = "sqt.company_id = %s and sw.id is not null"
        if not self.all_warehouses and self.warehouse_ids:
            location_conditions = ["sl.parent_path like %s"] * len(self.warehouse_ids)
            location_conditions = ' or '.join(location_conditions)
            where_query += f" and ({location_conditions}) "
        if not self.all_products and self.warehouse_ids:
            product_conditions = "sqt.product_id = any (%s)"
            where_query += f" and {product_conditions} "

        query = """
with stock as (select sm.product_id          as product_id,
                      coalesce(src_wh.id, 0) as src_warehouse_id,
                      coalesce(des_wh.id, 0) as dest_warehouse_id,
                      sum(sm.quantity_done)  as qty
               from stock_move sm
                        left join product_product on sm.product_id = product_product.id
                        left join stock_location des_lc on sm.location_dest_id = des_lc.id
                        left join stock_warehouse des_wh
                                  on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
                        left join stock_location src_lc on sm.location_id = src_lc.id
                        left join stock_warehouse src_wh
                                  on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
               group by sm.product_id, src_wh.id, des_wh.id),

     stock_by_warehouse as (select product_id,
                                   jsonb_object_agg(src_warehouse_id, qty)  as source_warehouse_qty,
                                   jsonb_object_agg(dest_warehouse_id, qty) as destination_warehouse_qty
                            from stock
                            group by product_id)
select product_id,
       source_warehouse_qty,
       destination_warehouse_qty
from stock_by_warehouse        
        """
        return query

    def _get_query_params(self):
        self.ensure_one()
        return []

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        return data
