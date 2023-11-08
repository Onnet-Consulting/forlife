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

    @api.model
    def execute_postgresql(self, query, param, build_dict):
        db_source = self.env['base.external.dbsource'].sudo().search([('connector', '=', 'postgresql')], limit=1)
        if db_source:
            rows, cols = db_source.execute_postgresql(query, param, build_dict)
            return self.build_dict(rows, cols) if build_dict else rows
        else:
            self._cr.execute(query, param)
            return self._cr.dictfetchall() if build_dict else self._cr.fetchall()

    @api.model
    def build_dict(self, rows, cols):
        return [{d: row[i] for i, d in enumerate(cols)} for row in rows]

    @api.model
    def get_attribute_code_config(self):
        return ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('attr_code_config') or '{}')

    @api.model
    def get_attribute_sequence_config(self):
        return ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('attr_sequence_config') or '[]')

    @api.model
    def get_attribute_value_by_product_id(self, product_ids, lang='vi_VN'):
        self._cr.execute(f"""
        select json_object_agg(product_id, attrs) as attrs_data
        from (select product_id                         as product_id,
                     json_object_agg(attrs_code, value) as attrs
              from (select pp.id                                                                                          as product_id,
                           pa.attrs_code                                                                                  as attrs_code,
                           array_agg(distinct coalesce(pav.name::json ->> '{lang}', pav.name::json ->> 'en_US')) as value
                    from product_template_attribute_line ptal
                             left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                             left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                             left join product_attribute pa on ptal.attribute_id = pa.id
                             left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                    where pa.attrs_code notnull {f'and pp.id = any(array{product_ids})' if product_ids else ''}
                    group by pp.id, pa.attrs_code) as att
              group by product_id) as data
        """)
        return self._cr.dictfetchone().get('attrs_data') or {}

    @api.model
    def get_attribute_value_by_product_barcode(self, barcode_list, lang='vi_VN'):
        self._cr.execute(f"""
                select json_object_agg(barcode, attrs) as attrs_data
                from (select barcode                            as barcode,
                             json_object_agg(attrs_code, value) as attrs
                      from (select pp.barcode                                                                                     as barcode,
                                   pa.attrs_code                                                                                  as attrs_code,
                                   array_agg(distinct coalesce(pav.name::json ->> '{lang}', pav.name::json ->> 'en_US')) as value
                            from product_template_attribute_line ptal
                                     left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                     left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                                     left join product_attribute pa on ptal.attribute_id = pa.id
                                     left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                            where pa.attrs_code notnull {f'and pp.barcode = any(array{barcode_list})' if barcode_list else ''}
                             and pp.barcode notnull
                            group by pp.barcode, pa.attrs_code) as att
                      group by barcode) as data
                """)
        return self._cr.dictfetchone().get('attrs_data') or {}

    @api.model
    def get_all_category_last_level(self, categ_ids):
        _categ_ids = []
        while categ_ids:
            cate_not_child = categ_ids.filtered(lambda s: not s.child_id)
            categ_ids = (categ_ids - cate_not_child).child_id
            _categ_ids.extend(cate_not_child.ids)
        return _categ_ids

    @api.model
    def create_ir_logging(self, name, message, **kwargs):
        IrLogging = self.env['ir.logging']
        IrLogging.sudo().create({
            'dbname': self._cr.dbname,
            'type': kwargs.get('type') or 'server',
            'name': name,
            'level': kwargs.get('level') or 'info',
            'path': kwargs.get('path') or 'path',
            'line': kwargs.get('line') or 'line',
            'func': kwargs.get('func') or 'func',
            'message': message,
        })

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
    def get_question_info(self, customer_phone, brand):
        comment_id = self.env['forlife.comment'].search([("customer_code", "=", customer_phone), ("brand", "=", brand), ("status", "=", 0)], limit=1)
        question_data = self.env['forlife.question'].search_read(
            [('id', '=', comment_id.question_id or 0)],
            ["header", "question1", "sub_quest1", "sub_quest2", "question2", "success1", "success2", "success3", "banner_question", "banner_success", "icon", "rate"]
        )
        res = dict(question_data[0]) if question_data else {}
        if res:
            res.update({'comment_id': comment_id.id})
        return res

    @api.model
    def update_net_promoter_score(self, comment_id, point, comment):
        comment_id = self.env['forlife.comment'].browse(comment_id)
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
     attribute_data as (select product_id                         as product_id,
                               json_object_agg(attrs_code, value) as attrs
                        from (select pp.id                                                                                    as product_id,
                                     pa.attrs_code                                                                            as attrs_code,
                                     array_agg(distinct coalesce(pav.name::json ->> '{self.env.user.lang}', pav.name::json ->> 'en_US')) as value
                              from product_template_attribute_line ptal
                                       left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                                       left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                                       left join product_attribute pa on ptal.attribute_id = pa.id
                                       left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                              where pp.id in (select id from products)
                                and pa.attrs_code notnull
                              group by pp.id, pa.attrs_code) as att
                        group by product_id),
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
     fixed_prices as (select row_number() over (PARTITION BY ppi.product_id order by campaign.from_date desc, ppi.id desc) as num, ppi.product_id, ppi.fixed_price
                      from promotion_pricelist_item ppi
                               join promotion_program program on ppi.program_id = program.id
                               join promotion_campaign campaign on campaign.id = program.campaign_id
                      where product_id in (select id from products)
                        and campaign.state = 'in_progress'
                        and now() between campaign.from_date and campaign.to_date
                        and ppi.active = true)

select coalesce(pp2.barcode, '')                                      as barcode,
       coalesce(pt2.name::json -> '{self.env.user.lang}', pt2.name::json -> 'en_US') as ten_san_pham,
       coalesce(sf.qty, 0)                                            as so_luong,
       REPLACE(REPLACE(REPLACE(coalesce(attrs::json ->> '{attr_value.get('mau_sac', '')}', ''), '"', ''), '[', ''), ']', '') as mau_sac,
       REPLACE(REPLACE(REPLACE(coalesce(attrs::json ->> '{attr_value.get('size', '')}', ''), '"', ''), '[', ''), ']', '') as size,
       REPLACE(REPLACE(REPLACE(coalesce(attrs::json ->> '{attr_value.get('doi_tuong', '')}', ''), '"', ''), '[', ''), ']', '') as gioi_tinh,
       coalesce(fixed_prices.fixed_price, pt2.list_price)             as gia_ban,
       '' as ma_tham_chieu
from products
         left join fixed_prices on products.id = fixed_prices.product_id and fixed_prices.num = 1
         left join stock_final sf on sf.product_id = products.id
         left join product_product pp2 on pp2.id = products.id
         left join product_template pt2 on pt2.id = pp2.product_tmpl_id
         left join attribute_data ad on ad.product_id = products.id
"""
        self._cr.execute(sql)
        return self._cr.dictfetchall()

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

    @api.model
    def get_point_history_information(self, phone_number, brand, type):
        if any([not phone_number, brand not in ('FMT', 'TKL'), type not in (0, 1)]):
            return []
        _point_type = {
            0: 'points_fl_order',
            1: 'points_used',
        }
        _brand = {
            'FMT': 'format',
            'TKL': 'forlife',
        }
        tz_offset = int(datetime.now(pytz.timezone(self.env.user.tz)).utcoffset().total_seconds() / 3600)

        sql = f"""
select coalesce(po.name, '')                                                      as ma_don_hang,
       coalesce(php.{_point_type.get(type)}, 0)                                   as diem,
       to_char(php.date_order + interval '{tz_offset} hours', 'HH:MM DD/MM/YYYY') as ngay_mua_hang
from partner_history_point php
         join res_partner rp on rp.id = php.partner_id
         left join pos_order po on po.id = php.pos_order_id
where php.store = '{_brand.get(brand)}'
  and rp.phone = '{phone_number}'
  and coalesce(php.{_point_type.get(type)}, 0) <> 0
order by php.date_order desc
"""
        return self.execute_postgresql(sql, [], True)

    @api.model
    def get_pos_order_information(self, phone_number, month, year, brand):
        if any([not phone_number, not brand, not (month in range(1, 13)), not isinstance(year, int)]):
            return []
        tz_offset = int(datetime.now(pytz.timezone(self.env.user.tz)).utcoffset().total_seconds() / 3600)

        sql = f"""
select po.pos_reference                                                    as ma_don_hang,
       store.code                                                          as ma_cua_hang,
       store.name                                                          as ten_cua_hang,
       to_char(po.date_order + interval '{tz_offset} hours', 'DD/MM/YYYY') as ngay_mua_hang,
       coalesce(po.amount_total, 0)                                        as so_tien_phai_tra,
       coalesce(po.point_order, 0)                                         as diem_tich_luy,
       coalesce(wh.street, '')                                             as dia_chi
from pos_order po
         join res_partner rp on rp.id = po.partner_id
         join pos_session ps on ps.id = po.session_id
         join pos_config pc on pc.id = ps.config_id
         join store on store.id = pc.store_id
         left join stock_warehouse wh on wh.id = store.warehouse_id
         join res_brand rb on rb.id = po.brand_id and rb.code = '{brand}'
where rp.phone = '{phone_number}'
  and to_char(po.date_order + interval '{tz_offset} hours', 'MM/YYYY') = '{"%.2d/%.4d" % (month, year)}'
"""
        return self.execute_postgresql(sql, [], True)

    @api.model
    def get_pos_order_detail_information(self, pos_reference):
        order = self.env['pos.order'].search([('pos_reference', '=', pos_reference)], limit=1)
        if not order:
            return []
        tz_offset = int(datetime.now(pytz.timezone(self.env.user.tz or 'Asia/Saigon')).utcoffset().total_seconds() / 3600)
        result = {
            'date_order': (order.date_order + timedelta(hours=tz_offset)).strftime('%d/%m/%Y %H:%M:%S') if order.date_order else '',
            'pos_reference': pos_reference or '',
            'cashier': order.user_id.name or '',
            'note': order.note or '',
        }
        promotion_code = set()
        promotion_amount = 0
        voucher_code = set()
        voucher_amount = 0
        amount_total = 0
        discount_total = 0
        qty_total = 0
        abs_qty_total = 0
        product_detail = dict()
        for line in order.lines.filtered(lambda f: not f.is_promotion and f.qty != 0):
            key = f"{'-' if line.qty < 0 else ''}{line.product_id.id}|{line.promotion_usage_ids.ids}|{int(line.original_price)}"
            product_detail.update({
                key: {
                    'product_name': (product_detail.get(key) or {}).get('product_name') or line.product_id.name or '',
                    'product_barcode': (product_detail.get(key) or {}).get('product_barcode') or line.product_id.barcode or '',
                    'qty': ((product_detail.get(key) or {}).get('qty') or 0) + line.qty,
                    'unit_price': (product_detail.get(key) or {}).get('unit_price') or line.original_price,
                    'discount': ((product_detail.get(key) or {}).get('discount') or 0) + line.money_is_reduced,
                    'amount': ((product_detail.get(key) or {}).get('amount') or 0) + line.subtotal_paid,
                }
            })
            amount_total += (line.qty * line.original_price) if line.qty > 0 else (line.subtotal_paid or 0)
            discount_total += (line.money_is_reduced or 0) if line.qty > 0 else 0
            qty_total += line.qty
            abs_qty_total += abs(line.qty)
            for promotion in line.promotion_usage_ids:
                if promotion.program_id.promotion_type == 'code' and promotion.code_id:
                    promotion_code.add(promotion.code_id.name) if promotion.code_id.name else None
                    promotion_amount += promotion.discount_total or 0
        for voucher in order.pos_voucher_line_ids:
            voucher_code.add(voucher.voucher_id.name)
            voucher_amount += voucher.price_residual_no_compute
        result.update({
            'promotion_code': ','.join(list(promotion_code)),
            'promotion_amount': promotion_amount,
            'voucher_code': ','.join(list(voucher_code)),
            'voucher_amount': voucher_amount,
            'qty_total': qty_total,
            'abs_qty_total': abs_qty_total,
            'amount_total': amount_total,
            'discount_total': discount_total,
            'product_detail': list(product_detail.values()),
            'amount_total_paid': amount_total - discount_total,
            'voucher_paid': sum(order.payment_ids.filtered(lambda s: s.payment_method_id.is_voucher).mapped('amount')),
            'point_total': order.total_point or 0,
        })
        return [result]

    @api.model
    def get_stock_quant_in_store(self, brand, barcode, province_id, district_id=False):
        if any([not brand, not barcode, not province_id]):
            return []
        sql = f"""
with products as (select id
                  from product_product
                  where barcode = '{barcode}'),
     warehouses as (select wh.id
                    from stock_warehouse wh
                    join res_brand rb on wh.brand_id = rb.id and rb.code = '{brand}'
                    where wh.state_id = {province_id}
                      {f'and wh.district_id = {district_id}' if district_id else ''}
                      ),
     stocks as (select sm1.product_id       as product_id,
                       s1.id                as s_id,
                       s1.name              as s_name,
                       s1.code              as s_code,
                       sum(sm1.product_qty) as qty
                from stock_move sm1
                         join stock_location sl1 on sl1.id = sm1.location_dest_id
                         join stock_warehouse wh1 on wh1.id = sl1.warehouse_id
                         join store s1 on wh1.id = s1.warehouse_id
                where sm1.state = 'done'
                  and wh1.id in (select id from warehouses)
                  and sm1.product_id in (select id from products)
                group by sm1.product_id, s1.id, s1.name, s1.code
                union all
                select sm2.product_id         as product_id,
                       s2.id                  as s_id,
                       s2.name                as s_name,
                       s2.code                as s_code,
                       - sum(sm2.product_qty) as qty
                from stock_move sm2
                         join stock_location sl2 on sl2.id = sm2.location_id
                         join stock_warehouse wh2 on wh2.id = sl2.warehouse_id
                         join store s2 on wh2.id = s2.warehouse_id
                where sm2.state = 'done'
                  and wh2.id in (select id from warehouses)
                  and sm2.product_id in (select id from products)
                group by sm2.product_id, s2.id, s2.name, s2.code)
select s_id     as id_cua_hang,
       s_name   as ten_cua_hang,
       s_code   as ma_cua_hang,
       sum(qty) as so_luong
from stocks
group by s_id, s_name, s_code
"""
        return self.execute_postgresql(sql, [], True)

    @api.model
    def get_customer_information(self, phone_number):
        if not phone_number:
            return []
        sql = f"""
with customers as (select rp.id
                   from res_partner rp
                   join res_partner_group rpg on rpg.id = rp.group_id
                   where phone = '{phone_number}' and rpg.code = 'C'),
     retail_types as (select customers.id    as customer_id,
                             array_agg(name) as retail_type
                      from res_partner_retail rpr
                               join res_partner_res_partner_retail_rel rel
                                    on rel.res_partner_retail_id = rpr.id
                               join customers on customers.id = rel.res_partner_id
                      group by customers.id),
     ranks as (select pcr.customer_id as customer_id,
                      cr.name         as rank_name,
                      rb.code         as brand
               from partner_card_rank pcr
                        join res_brand rb on rb.id = pcr.brand_id
                        join card_rank cr on cr.id = pcr.card_rank_id
               where pcr.customer_id in (select id from customers)
               order by pcr.customer_id),
     rank_by_customer as (select customer_id,
                                 json_object_agg(brand, rank_name) as rank
                          from ranks
                          group by customer_id)
select rp.id                                          as id_kh,
       coalesce(rp.code, '')                          as ma_kh,
       coalesce(rp.barcode, '')                       as barcode_kh,
       coalesce(rp.name, '')                          as ten_kh,
       coalesce(rp.phone, '')                         as sdt_kh,
       coalesce(rbc.rank, '{{}}')                       as hang_the,
       coalesce(rt.retail_type, '{{}}')                 as loai_khach_le,
       coalesce(rp.total_points_available_forlife, 0) as diem_tokyolife,
       coalesce(rp.total_points_available_format, 0)  as diem_format
from res_partner rp
         left join rank_by_customer rbc on rp.id = rbc.customer_id
         left join retail_types rt on rp.id = rt.customer_id
where rp.id in (select id from customers)    
"""
        return self.execute_postgresql(sql, [], True)

    @api.model
    def action_active_voucher(self, voucher_code):
        if not voucher_code:
            return {"message": f"Mã voucher không hợp lệ"}
        voucher = self.env['voucher.voucher'].search([('name', '=', voucher_code)])
        if voucher:
            voucher.sudo().write({'state_app': True})
            return {"message": f"Kích hoạt thành công mã voucher '{voucher_code}'"}
        else:
            return {"message": f"Kích hoạt không thành công, mã voucher '{voucher_code}' không được tìm thấy"}

    @api.model
    def get_country_state_with_brand_code(self, brand_code):
        sql = f"""
            select rcs.id as id, rcs.code as code, rcs.name as name
            from res_country_state rcs
                     join res_country rc on rcs.country_id = rc.id and rc.code = 'VN'
                     join stock_warehouse wh on rcs.id = wh.state_id
                     join store on wh.id = store.warehouse_id
                     join res_brand rb on store.brand_id = rb.id and rb.code = '{brand_code}'
            group by rcs.id, rcs.code, rcs.name;
        """
        return self.execute_postgresql(sql, [], True)

    @api.model
    def get_employee_by_uid(self, uid):
        self._cr.execute(f'select * from hr_employee where user_id = {uid} and active = true limit 1')
        return self._cr.dictfetchone() or {}

    @api.model
    def get_multi_employee_by_list_uid(self, uids):
        if not uids:
            return {}
        self._cr.execute(f'select json_object_agg(user_id, hr_employee.*) employees from hr_employee where user_id = any(array{uids}) and active = true')
        return self._cr.dictfetchall()[0].get('employees') or {}


