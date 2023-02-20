# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ReportStockSalePriceByWarehouse(models.TransientModel):
    _name = 'report.stock.sale.price.by.warehouse'
    _inherit = 'report.base'
    _description = 'Report stock with sale price by warehouse'

    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')

    def view_report(self):
        self.ensure_one()
        action = self.env.ref('forlife_report.report_stock_price_by_warehouse_client_action').read()[0]
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

        query = f"""
with stock_product as
         (select sqt.product_id    as product_id,
                 sw.id             as warehouse_id,
                 sum(sqt.quantity) as quantity

          from stock_quant sqt
                   left join product_product pp on sqt.product_id = pp.id
                   left join stock_location sl on sqt.location_id = sl.id
                   left join stock_warehouse sw
                             on sl.parent_path like concat('%%/', sw.view_location_id, '/%%')
          where {where_query}
          group by sqt.product_id,
                   sw.id
         )
select pp.id                                                                   as product_id,
       pp.barcode                                                              as product_barcode,
       coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US') as product_name,
       sw.id                                                                   as warehouse_id,
       sw.name                                                                 as warehouse_name,
       stp.quantity                                                            as quantity
from stock_product stp
         left join product_product pp on pp.id = stp.product_id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join stock_warehouse sw on sw.id = stp.warehouse_id
        """

        return query

    def _get_query_params(self):
        self.ensure_one()
        params = [self.company_id.id]
        if not self.all_warehouses and self.warehouse_ids:
            params.extend(
                [f'%/{view_location_id}/%' for view_location_id in self.warehouse_ids.mapped('view_location_id').ids])

        if not self.all_products and self.product_ids:
            params.append(self.product_ids.ids)
        return params

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        data_by_product_id = {}
        detail_data_by_product_id = {}
        for line in data:
            product_id = line.get('product_id')
            if product_id not in data_by_product_id:
                data_by_product_id[product_id] = line
            else:
                data_by_product_id[product_id]['quantity'] += line['quantity']

            detail_data = {
                "warehouse_name": line.get('warehouse_name'),
                "quantity": line.get("quantity")
            }
            if product_id not in detail_data_by_product_id:
                detail_data_by_product_id[product_id] = [detail_data]
            else:
                detail_data_by_product_id[product_id].append(detail_data)
        return {
            "product_data": list(data_by_product_id.values()),
            "detail_data_by_product_id": detail_data_by_product_id
        }
