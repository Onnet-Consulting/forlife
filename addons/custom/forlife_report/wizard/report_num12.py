# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from dateutil.relativedelta import relativedelta

TITLE_LAYER1 = ['STT', 'Cửa hàng', 'Hạng', 'Tổng số lượng khách hàng']
TITLE_LAYER2 = [
    'STT', 'Cửa hàng', 'Mã khách', 'Tên khách hàng', 'Giới tính', 'Điện thoại', 'Ngày mua gần nhất',
    'Doanh thu đơn hàng gần nhất', 'Hạng hiện tại', 'Tổng doanh thu mua sắm', 'Thời gian không mua sắm',
]


class ReportNum12(models.TransientModel):
    _name = 'report.num12'
    _inherit = 'report.base'
    _description = 'Report customers not buying'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    to_date = fields.Date('To date', required=True)
    store_ids = fields.Many2many('store', string='Store')
    number_of_days = fields.Integer(string='Number of days', default=90)

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        store_condition = f'where xx.store_id = any (array{self.store_ids.ids})' if self.store_ids else ''
        query = f"""        
with tong_dt_ms_tb as (
    select partner_card_rank_id,
        sum(value_to_upper) as total_value
    from partner_card_rank_line
    where value_to_upper <> 0 and {format_date_query("order_date", tz_offset)} < '{self.to_date}'
    group by partner_card_rank_id
),
data_dt as (
    select partner_card_rank_id,
        value_to_upper,
        row_number() over (PARTITION BY partner_card_rank_id ORDER BY real_date desc) as num
    from partner_card_rank_line
    where value_to_upper <> 0 and {format_date_query("order_date", tz_offset)} < '{self.to_date}'
),
dt_dh_gn_tb as (
    select partner_card_rank_id, value_to_upper from data_dt where num = 1
),
part_card_rank_data1 as (
    select pcr.customer_id,
        sfo.store_id  as store_id,
        pcr.card_rank_id                                                                                as card_rank_id,
        to_char(pcr.last_order_date + interval '7 hours', 'DD/MM/YYYY') 								as last_order_date,
        coalesce(dt_gn.value_to_upper)                      								            as dt_dh_gn,
        coalesce(dt.total_value, 0)                                                      	            as tong_dt_ms,
        to_date('2023-05-23', 'YYYY-MM-DD')::date - (pcr.last_order_date + interval '7 hours')::date    as tg_khong_ms
    from partner_card_rank pcr
        left join store_first_order sfo on sfo.customer_id = pcr.customer_id and sfo.brand_id = {self.brand_id.id}
        left join tong_dt_ms_tb dt on dt.partner_card_rank_id = pcr.id
        left join dt_dh_gn_tb dt_gn on dt_gn.partner_card_rank_id = pcr.id
    where pcr.brand_id = {self.brand_id.id}
        and {format_date_query("pcr.last_order_date", tz_offset)} < '{self.to_date - relativedelta(days=self.number_of_days)}'
),
part_card_rank_data2 as (
    select concat(xx.store_id, '_', xx.card_rank_id) 				                                                            as key_data,
    sto.name                                         		                                                                    as store_name,
    array[
        coalesce(rp.internal_code, ''),
        coalesce(rp.name, ''),
        case
            when rp.gender = 'male' then 'Nam'
            when rp.gender = 'female' then 'Nữ'
            when rp.gender = 'other' then 'Khác' else '' end,
        coalesce(rp.phone)
    ]                                            														                        as customer_info,
    xx.last_order_date                                                                                                          as last_order_date,
    xx.dt_dh_gn                                                                                                                 as dt_dh_gn,
    cr.name                                                                                                                     as rank_name,
    xx.tong_dt_ms                                                                                                               as tong_dt_ms,
    xx.tg_khong_ms                                                                                                              as tg_khong_ms
    from part_card_rank_data1 xx
        left join store sto on sto.id = xx.store_id
        left join card_rank cr on cr.id = xx.card_rank_id
        left join res_partner rp on rp.id = xx.customer_id
    {store_condition} 
),
count_data_by_store_and_card_rank as (
    select key_data,
            store_name,
            rank_name,
            count(1) as total_customer
    from part_card_rank_data2 group by key_data, store_name, rank_name
),
aggregation_date_by_key as (
    select key_data, array_agg(to_json(x_value.*)) as value_detail
    from part_card_rank_data2 as x_value group by key_data
)
select coalesce(x1.key_data, x2.key_data) as key_data,
        x2.store_name,
        x2.rank_name,
        x2.total_customer,
        x1.value_detail
from aggregation_date_by_key x1
join count_data_by_store_and_card_rank x2 on x1.key_data = x2.key_data"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLE_LAYER1,
            'title_layer2': TITLE_LAYER2,
            "data": data,
        })
        return values
