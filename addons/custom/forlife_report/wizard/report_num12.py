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
with part_card_rank_data1 as (
    select pcr.customer_id,
        (select store_id from store_first_order where brand_id = {self.brand_id.id} and customer_id = pcr.customer_id)  as store_id,
        pcr.card_rank_id                                                                                                as card_rank_id,
        to_char(pcr.last_order_date + interval '{tz_offset} hours', 'DD/MM/YYYY') 								        as last_order_date,
        (select value_to_upper from partner_card_rank_line
         where partner_card_rank_id = pcr.id and order_id notnull order by real_date desc limit 1)                      as dt_dh_gn,
         (select sum(value_to_upper) from partner_card_rank_line
         where partner_card_rank_id = pcr.id and order_id notnull)                                                      as tong_dt_ms,
         to_date('{self.to_date}', 'YYYY-MM-DD')::date - (pcr.last_order_date + interval '7 hours')::date               as tg_khong_ms
    from partner_card_rank pcr
    where pcr.brand_id = {self.brand_id.id}
        and {format_date_query("pcr.last_order_date", tz_offset)} < '{self.to_date - relativedelta(days=self.number_of_days)}'
),
part_card_rank_data2 as (
    select concat(xx.store_id, '_', xx.card_rank_id) 				                                                            as key_data,
    (select name from store where id = xx.store_id) 		                                                                    as store_name,
    (select array[
        coalesce(internal_code, ''),
          coalesce(name, ''),
          case when gender = 'male' then 'Nam' when gender = 'female' then 'Nữ' when gender = 'other' then 'Khác' else '' end,
          coalesce(phone)
    ] from res_partner where id = xx.customer_id) 														                        as customer_info,
    xx.last_order_date                                                                                                          as last_order_date,
    xx.dt_dh_gn                                                                                                                 as dt_dh_gn,
    (select name from card_rank where id = xx.card_rank_id)                                                                     as rank_name,
    xx.tong_dt_ms                                                                                                               as tong_dt_ms,
    xx.tg_khong_ms                                                                                                              as tg_khong_ms
    from part_card_rank_data1 xx
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

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        query = self._get_query()
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLE_LAYER1,
            'title_layer2': TITLE_LAYER2,
            "data": data,
        })
        return values
