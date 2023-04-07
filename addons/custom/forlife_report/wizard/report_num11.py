# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from dateutil.relativedelta import relativedelta

TITLES = [
    'STT', 'Cửa hàng', 'Mã khách', 'Tên khách hàng', 'Ngày sinh', 'Điện thoại', 'Ngày mua đầu kỳ',
    'Ngày mua gần nhất', 'Ngày cuối kỳ', 'Doanh thu phát sinh', 'Giá trị cần đạt', 'Hạng hiện tại', 'Hạng mới',
]


class ReportNum11(models.TransientModel):
    _name = 'report.num11'
    _inherit = 'report.base'
    _description = 'About to rank up'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    to_date = fields.Date('To date', required=True)
    from_rank_ids = fields.Many2many('card.rank', string='From rank')
    store_ids = fields.Many2many('store', string='Store')
    customer_ids = fields.Many2many('res.partner', string='Customer', domain=lambda self: [('group_id', 'in', self.env['res.partner.group'].search([('code', '=', 'C')]).ids)])
    number_of_days = fields.Integer(string='Number of days', default=20)

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        rank_condition = f" and current_rank_id = any (array{self.from_rank_ids.ids})\n" if self.from_rank_ids else ''
        pcr_condition = f"and customer_id = any (array{self.customer_ids.ids})\n" if self.customer_ids else ''
        pcr_condition += '' if not self.store_ids else f"""and customer_id in (select customer_id from store_first_order
         where store_id = any (array{self.store_ids.ids}))\n"""
        query = f"""
with program_cr as (
    with program_cr_temp1 as (
        select mc.id,
            mc.time_set_rank,
            mc.card_rank_id,
            mc.min_turnover,
            coalesce(mc.min_turnover, 0) - coalesce(mc.value_remind, 0) as x_value_remind,
            (select priority from card_rank where id = mc.card_rank_id) as priority
        from member_card mc
        where mc.brand_id = {self.brand_id.id}
            and '{self.to_date}' between mc.from_date and mc.to_date
        order by mc.min_turnover desc
    ),
    program_cr_temp2 as (
        select xx.*,
                (select card_rank_id from program_cr_temp1
        where priority < xx.priority order by priority desc limit 1) as previous_rank_id
        from program_cr_temp1 xx
    )
    select * from program_cr_temp2 where previous_rank_id notnull
),
current_partner_card_rank as (
    with temp_tb1 as (
        select id as pcr_id,
            customer_id,
            (select old_card_rank_id from partner_card_rank_line
                where partner_card_rank_id = x_pcr.id and order_id notnull
                 and {format_date_query("order_date", tz_offset)} <= '{self.to_date}'
                order by real_date desc, id desc limit 1)                               as current_rank_id
        from partner_card_rank x_pcr
        where brand_id = {self.brand_id.id} and {format_date_query("create_date", tz_offset)} <= '{self.to_date}'
        {pcr_condition}
    )
    select * from temp_tb1 where current_rank_id notnull
     {rank_condition}
),
current_partner_card_rank_by_period as (
    select cpcr.*,
           pcr.min_turnover,
           pcr.x_value_remind,
           (to_date('{self.to_date + relativedelta(days=self.number_of_days)}',
            'YYYY-MM-DD') - (coalesce(pcr.time_set_rank, 0) || ' d')::interval)::date               as ngay_mua_dk,
           to_date('{self.to_date + relativedelta(days=self.number_of_days)}', 'YYYY-MM-DD')::date  as ngay_ck
    from current_partner_card_rank cpcr
        join program_cr pcr on pcr.previous_rank_id = cpcr.current_rank_id
),
data_final as (
    select
        (select coalesce(name, '')
         from store where id = (select store_id from store_first_order
         where customer_id = rp.id and brand_id = {self.brand_id.id})
        )                                                                                   as store_name,
        to_char(cpcr.ngay_mua_dk, 'DD/MM/YYYY')                                             as ngay_mua_dk,
        (select to_char(order_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')
            from partner_card_rank_line
             where partner_card_rank_id = cpcr.pcr_id and order_id notnull
                and {format_date_query("order_date", tz_offset)} <= '{self.to_date}'
             order by order_date desc limit 1)                                              as ngay_mua_gn,
        to_char(cpcr.ngay_ck, 'DD/MM/YYYY')                                                 as ngay_ck,
        (select sum(value_to_upper) from partner_card_rank_line
            where partner_card_rank_id = cpcr.pcr_id and order_id notnull
                 and order_date between cpcr.ngay_mua_dk and '{self.to_date}'
        )                                                                                   as dt_ps,
        cpcr.min_turnover - (select sum(value_to_upper) from partner_card_rank_line
            where partner_card_rank_id = cpcr.pcr_id and order_id notnull
                 and order_date between cpcr.ngay_mua_dk and '{self.to_date}'
        )                                                                                   as gt_cd,
        (select name from card_rank where id = cpcr.current_rank_id)                        as current_rank,
        array[coalesce(rp.internal_code, ''),
              coalesce(rp.name, ''),
              coalesce(to_char(rp.birthday + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY'), ''),
              coalesce(rp.phone)]                                                           as customer_info,
        cpcr.x_value_remind                                                                 as x_value_remind
    from current_partner_card_rank_by_period cpcr
        join res_partner rp on rp.id = cpcr.customer_id
)
select * from data_final where x_value_remind >= dt_ps
        """
        return query

    def get_data(self):
        self.ensure_one()
        values = dict(super().get_data())
        query = self._get_query()
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values
