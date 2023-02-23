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

    def _get_query_params(self):
        self.ensure_one()
        params = [self.company_id.id]
        if not self.all_warehouses and self.warehouse_ids:
            params.extend([self.warehouse_ids.ids] * 2)
        if not self.all_products and self.product_ids:
            params.append(self.product_ids.ids)
        if self.from_date:
            params.append(self.from_date)
        if self.to_date:
            params.append(self.to_date)
        return params

    def _get_query(self):
        # FIXME: something wrong - total quantity (stock) get from stock.move is not correct
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        where_query = "sm.company_id = %s and sm.state = 'done'"
        if not self.all_warehouses and self.warehouse_ids:
            warehouse_conditions = "(src_wh.id = any (%s) or des_wh.id = any (%s))"
            where_query += f" and {warehouse_conditions} "
        if not self.all_products and self.product_ids:
            product_conditions = "sm.product_id = any (%s)"
            where_query += f" and {product_conditions} "
        if self.from_date:
            where_query += f" and sm.date + interval '{tz_offset} hours' >= %s"
        if self.to_date:
            where_query += f" and sm.date + interval '{tz_offset} hours' <= %s"

        query = f"""
with stock as (select sm.product_id          as product_id,
                      coalesce(src_wh.id, 0) as src_warehouse_id,
                      coalesce(des_wh.id, 0) as dest_warehouse_id,
                      sum(sm.quantity_done)  as qty
               from stock_move sm
                        left join stock_location des_lc on sm.location_dest_id = des_lc.id
                        left join stock_warehouse des_wh
                                  on des_lc.parent_path like concat('%%/', des_wh.view_location_id, '/%%')
                        left join stock_location src_lc on sm.location_id = src_lc.id
                        left join stock_warehouse src_wh
                                  on src_lc.parent_path like concat('%%/', src_wh.view_location_id, '/%%')
               where {where_query}
               group by sm.product_id, src_wh.id, des_wh.id),

     stock_by_warehouse as (select product_id,
                                   jsonb_object_agg(src_warehouse_id, qty)  as source_warehouse_qty,
                                   jsonb_object_agg(dest_warehouse_id, qty) as destination_warehouse_qty
                            from stock
                            group by product_id)
select sbw.product_id                                                            as product_id,
       sbw.source_warehouse_qty                                                  as source_warehouse_qty,
       sbw.destination_warehouse_qty                                             as destination_warehouse_qty,
       pp.barcode                                                                as product_barcode,
       coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
       coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as uom_name
from stock_by_warehouse sbw
         left join product_product pp on sbw.product_id = pp.id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join uom_uom uom on pt.uom_id = uom.id
order by sbw.product_id
        """
        return query

    def get_warehouse_data(self):
        if not self.all_warehouses and self.warehouse_ids:
            query = """
                select id,name from stock_warehouse where id = any (%s)
            """
            params = [self.warehouse_ids.ids]
        else:
            query = """
                select id,name from stock_warehouse
            """
            params = []
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        warehouse_ids = []
        warehouse_names = []
        warehouse_name_by_id = {}
        for warehouse in data:
            wh_name = warehouse['name']
            wh_id = str(warehouse['id'])
            warehouse_ids.append(wh_id)
            warehouse_names.append(wh_name)
            warehouse_name_by_id[wh_id] = wh_name
        return dict(warehouse_name_by_id=warehouse_name_by_id,
                    warehouse_names=warehouse_names,
                    warehouse_ids=warehouse_ids)

    def format_data(self, data):
        for line in data:
            source_warehouse_qty = line.pop('source_warehouse_qty')
            destination_warehouse_qty = line.pop('destination_warehouse_qty')
            source_warehouse_qty.pop('0', None)
            destination_warehouse_qty.pop('0', None)
            product_qty_by_warehouse = {}
            total_qty = 0
            warehouse_ids = {**source_warehouse_qty, **destination_warehouse_qty}.keys()
            for wh_id in warehouse_ids:
                wh_qty = destination_warehouse_qty.get(wh_id, 0) - source_warehouse_qty.get(wh_id, 0)
                product_qty_by_warehouse[wh_id] = wh_qty
                total_qty += wh_qty

            line['product_qty_by_warehouse'] = product_qty_by_warehouse
            line['total_qty'] = total_qty
        return data

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        data = self.format_data(data)
        warehouse_data = self.get_warehouse_data()
        return {"data": data, **warehouse_data}
