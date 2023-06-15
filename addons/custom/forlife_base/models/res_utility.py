# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DDF, DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime, timedelta
import xlrd
import pytz
import ast


def convert_localize_datetime(value, tz):
    tz_name = tz or 'UTC'
    utc_datetime = pytz.utc.localize(value, is_dst=False)
    try:
        context_tz = pytz.timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime
    return localized_datetime


class ResUtility(models.AbstractModel):
    _name = 'res.utility'
    _description = 'Utility Methods'

    @api.model
    def read_xls_book(self, book, sheet_index):
        sheet = book.sheet_by_index(sheet_index)
        # emulate Sheet.get_rows for pre-0.9.4
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DDF)
                        if is_datetime
                        else dt.strftime(DF)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s") % {
                            'row': rowx,
                            'col': colx,
                            'cell_value': xlrd.error_text_from_code.get(cell.value,
                                                                        _("unknown error code %s") % cell.value)
                        }
                    )
                else:
                    values.append(cell.value)
            yield values

    def execute_postgresql(self, query, param, build_dict):
        db_source = self.env['base.external.dbsource'].sudo().search([('connector', '=', 'postgresql')], limit=1)
        if db_source:
            rows, cols = db_source.execute_postgresql(query, param, build_dict)
            return self.build_dict(rows, cols) if build_dict else rows
        else:
            self._cr.execute(query, param)
            return self._cr.dictfetchall() if build_dict else self._cr.fetchall()

    def build_dict(self, rows, cols):
        return [{d: row[i] for i, d in enumerate(cols)} for row in rows]

    def get_attribute_code_config(self):
        return ast.literal_eval(self.env.ref('forlife_base.attr_code_default').attr_code or '{}')

    @api.model
    def get_warehouse_type_info(self):
        return self.env['stock.warehouse.type'].search_read([], ['id', 'code', 'name'])

    @api.model
    def get_allowed_company(self):
        return [{
            'id': c.id,
            'name': c.name,
            'code': c.code,
        } for c in self.env.user.company_ids]

    @api.model
    def get_warehouse_info(self, wh_type_code, company_code):
        return self.env['stock.warehouse'].search_read([('whs_type.code', '=', wh_type_code), ('company_id.code', '=', company_code)], ['id', 'code', 'name'])

    @api.model
    def get_stock_inventory_by_wh_id(self, wh_id):
        data = self.env['stock.inventory'].search([('company_id', '=', self.env.user.company_id.id),
                                                   ('warehouse_id', '=', wh_id),
                                                   ('state', 'in', ('first_inv', 'second_inv'))])
        return [{
            'id_phieu_kk': inv.id,
            'so_phieu_kk': inv.name,
            'dia_diem': inv.mapped('location_ids.complete_name'),
            'trang_thai': 'kk_b1' if inv.state == 'first_inv' else 'kk_b2',
            'tong_ton': sum(inv.mapped('line_ids.theoretical_qty'))
        } for inv in data]

    @api.model
    def get_stock_inventory_detail(self, inv_id):
        data = self.env['stock.inventory'].search([('id', '=', inv_id)])
        return [{
            'barcode': line.product_id.barcode,
            'quantity': line.theoretical_qty
        } for line in data.mapped('line_ids')]

    @api.model
    def get_question_info(self, customer_phone, brand):
        question_id = self.env['forlife.comment'].search([("customer_code", "=", customer_phone), ("brand", "=", brand), ("status", "=", 0)], limit=1).question_id or 0
        question_data = self.env['forlife.question'].search_read(
            [('id', '=', question_id)],
            ["header", "question1", "sub_quest1", "sub_quest2", "question2", "success1", "success2", "success3", "banner_question", "banner_success", "icon", "rate"]
        )
        return question_data[0] if question_data else {}

    @api.model
    def update_net_promoter_score(self, customer_phone, brand, point, comment):
        comment_id = self.env['forlife.comment'].search([("customer_code", "=", customer_phone), ("brand", "=", brand), ("status", "=", 0)], limit=1)
        if comment_id:
            comment_id.with_context(update_comment=True).sudo().write({
                'point': point,
                'comment': comment,
                'status': 1,
                'comment_date': fields.Datetime.now(),
            })
            return {
                'id': comment_id.id,
                'phone': comment_id.customer_code,
                'point': comment_id.point,
                'comment': comment_id.comment,
            }
        return False

    @api.model
    def get_stock_quant_in_warehouse_by_barcode(self, wh_id, barcode):
        if any([not wh_id, not barcode]):
            return []
        attr_value = self.get_attribute_code_config()
        sql = f"""
with products as (select id
                  from product_product
                  where product_tmpl_id in (select id
                                            from product_template
                                            where sku_code in (select distinct pt.sku_code
                                                               from product_product pp
                                                                        join product_template pt on pp.product_tmpl_id = pt.id
                                                               where pp.barcode = '{barcode}'))),
     companys as (select company_id as id from stock_warehouse where id = {wh_id}),
     locatoins as (select id from stock_location where warehouse_id = {wh_id}),
     attribute_data as (select pp.id                                                                                as product_id,
                               pa.attrs_code                                                                        as attrs_code,
                               array_agg(coalesce(pav.name::json -> 'vi_VN', pav.name::json -> 'en_US')) as value
                        from product_template_attribute_line ptal
                                 left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                 left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                                 left join product_attribute pa on ptal.attribute_id = pa.id
                                 left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                        where pp.id in (select id from products)
                        group by pp.id, pa.attrs_code),
     stocks as (select product_id as product_id, sum(product_qty) as qty
                from stock_move
                where state = 'done'
                  and company_id in (select id from companys)
                  and location_dest_id in (select id from locatoins)
                  and product_id in (select id from products)
                group by product_id
                union all
                select product_id as product_id, - sum(product_qty) as qty
                from stock_move
                where state = 'done'
                  and company_id in (select id from companys)
                  and location_id in (select id from locatoins)
                  and product_id in (select id from products)
                group by product_id),
     stock_final as (select product_id, sum(qty) as qty
                     from stocks
                     group by product_id),
     fixed_prices as (select row_number() over (PARTITION BY ppi.product_id order by campaign.from_date, ppi.id desc) as num, ppi.product_id, ppi.fixed_price
                      from promotion_pricelist_item ppi
                               join promotion_program program on ppi.program_id = program.id
                               join promotion_campaign campaign on campaign.id = program.campaign_id
                      where product_id in (select id from products)
                        and campaign.state = 'in_progress'
                        and now() between campaign.from_date and campaign.to_date)

select coalesce(pp2.barcode, '')                                      as barcode,
       coalesce(pt2.name::json -> 'vi_VN', pt2.name::json -> 'en_US') as ten_san_pham,
       coalesce(sf.qty, 0)                                            as so_luong,
       coalesce(attr_color.value, array[]::json[])                                 as mau_sac,
       coalesce(attr_size.value, array[]::json[])                                  as size,
       coalesce(attr_gender.value, array[]::json[])                                as gioi_tinh,
       coalesce(fixed_prices.fixed_price, pt2.list_price)             as gia_ban
from products
         left join fixed_prices on products.id = fixed_prices.product_id and fixed_prices.num = 1
         left join stock_final sf on sf.product_id = products.id
         left join product_product pp2 on pp2.id = products.id
         left join product_template pt2 on pt2.id = pp2.product_tmpl_id
         left join attribute_data attr_color on attr_color.product_id = products.id and attr_color.attrs_code = '{attr_value.get('mau_sac', '')}'
         left join attribute_data attr_size on attr_size.product_id = products.id and attr_size.attrs_code = '{attr_value.get('size', '')}'
         left join attribute_data attr_gender on attr_gender.product_id = products.id and attr_gender.attrs_code = '{attr_value.get('doi_tuong', '')}'
"""
        return self.execute_postgresql(sql, [], True)

    @api.model
    def get_stock_warehouse_info_by_barcode(self, wh_type_code, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        wh_type = self.env['stock.warehouse.type'].search([('code', '=', wh_type_code)])
        if any([not product, not wh_type, not wh_type_code, not barcode]):
            return []
        stock_move = self.env['stock.move'].search(['&', '&', ('product_id', '=', product.id), ('state', '=', 'done'),
                                                    '|', ('location_id.warehouse_id.whs_type', '=', wh_type.id),
                                                    ('location_dest_id.warehouse_id.whs_type', '=', wh_type.id)])
        wh_out_ids = stock_move.mapped('location_id.warehouse_id').filtered(lambda f: f.whs_type.id == wh_type.id)
        wh_in_ids = stock_move.mapped('location_dest_id.warehouse_id').filtered(lambda f: f.whs_type.id == wh_type.id)
        result = []
        for wh in set(wh_out_ids.ids + wh_in_ids.ids):
            sm_out = sum(stock_move.filtered(lambda x: x.location_id.warehouse_id.id == wh).mapped('product_qty'))
            sm_in = sum(stock_move.filtered(lambda x: x.location_dest_id.warehouse_id.id == wh).mapped('product_qty'))
            if sm_out < sm_in:
                _wh = wh_out_ids.filtered(lambda w: w.id == wh) or wh_in_ids.filtered(lambda w: w.id == wh)
                result.append({
                    'ma_kho': _wh.code,
                    'ten_kho': _wh.name,
                    'so_luong': sm_in - sm_out,
                })
        return result
