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
        pcr_condition = f"and x_pcr.customer_id = any (array{self.customer_ids.ids})\n" if self.customer_ids else ''
        pcr_condition += '' if not self.store_ids else f"""and x_pcr.customer_id in (select customer_id from store_first_order
                 where store_id = any (array{self.store_ids.ids}) and brand_id = {self.brand_id.id})\n"""
        query = f"""
with program_cr as (
    with program_cr_temp1 as (
        select
            mc.id,
            mc.time_set_rank,
            mc.card_rank_id,
            mc.min_turnover,
            coalesce(mc.value_remind, 0) as value_remind,
            cr.priority
        from member_card mc
            join card_rank cr on cr.id = mc.card_rank_id
        where mc.brand_id = {self.brand_id.id}
            and '{self.to_date}' between mc.from_date and mc.to_date
        order by mc.min_turnover desc
    ),
    program_cr_temp2 as (
        select
            xx.*,
            (select card_rank_id from program_cr_temp1
        where priority < xx.priority order by priority desc limit 1) as previous_rank_id
        from program_cr_temp1 xx
    )
    select * from program_cr_temp2 where previous_rank_id notnull
),
current_partner_card_rank as (
    with temp_tb1 as (
        select
            x_pcr.id as pcr_id,
            x_pcr.customer_id as customer_id,
            x_pcrl.new_card_rank_id as current_rank_id,
            row_number() over (PARTITION BY x_pcr.id ORDER BY x_pcrl.real_date desc) as row_x
        from partner_card_rank x_pcr
            join partner_card_rank_line x_pcrl on x_pcrl.partner_card_rank_id = x_pcr.id
        where x_pcr.brand_id = {self.brand_id.id}
            and {format_date_query("x_pcrl.order_date", tz_offset)} <= '{self.to_date}'
        {pcr_condition}
    )
    select pcr_id, customer_id, current_rank_id
    from temp_tb1
    where current_rank_id in (select previous_rank_id from program_cr) and row_x = 1
        {rank_condition}
),
current_partner_card_rank_by_period as (
    select
        cpcr.*,
        pcr.min_turnover,
        pcr.value_remind,
        (to_date('{self.to_date + relativedelta(days=self.number_of_days)}',
            'YYYY-MM-DD') - (coalesce(pcr.time_set_rank, 0) || ' d')::interval)::date            as ngay_mua_dk,
        to_date('{self.to_date + relativedelta(days=self.number_of_days)}', 'YYYY-MM-DD')::date  as ngay_ck,
        pcr.card_rank_id                                                                         as new_cr_id
    from current_partner_card_rank cpcr
        join program_cr pcr on pcr.previous_rank_id = cpcr.current_rank_id
),
ngay_mua_gn_by_id as (
    with ngay_mua_gn_x as (
        select
            partner_card_rank_id                                                            as pcr_id,
            to_char(order_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')             as date_order,
            new_card_rank_id                                                                as current_rank_id,
            row_number() over (PARTITION BY partner_card_rank_id ORDER BY real_date desc)   as row_x
        from partner_card_rank_line
        where value_to_upper > 0
            and {format_date_query("order_date", tz_offset)} <= '{self.to_date}'
    )
    select pcr_id, date_order
    from ngay_mua_gn_x
    where row_x = 1 {rank_condition}
    
),
value_to_upper_by_customer as (
    select
        partner_card_rank_id 			 as pcr_id,
        coalesce(sum(value_to_upper), 0) as amount
    from partner_card_rank_line pcrl
        join current_partner_card_rank_by_period cpcr on pcrl.partner_card_rank_id = cpcr.pcr_id
    where pcrl.order_date between cpcr.ngay_mua_dk and '{self.to_date}'
    group by partner_card_rank_id
),
data_final as (
    select
        st.name                                                                             as store_name,
        to_char(cpcr.ngay_mua_dk, 'DD/MM/YYYY')                                             as ngay_mua_dk,
        nmgn.date_order                                                                     as ngay_mua_gn,
        to_char(cpcr.ngay_ck, 'DD/MM/YYYY')                                                 as ngay_ck,
        vtu.amount                                                                          as dt_ps,
        cpcr.min_turnover                                                                   as min_turnover,
        c_cr.name                                                                           as current_rank,
        n_cr.name                                                                           as new_rank,
        array[coalesce(rp.internal_code, ''),
              coalesce(rp.name, ''),
              coalesce(to_char(rp.birthday + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY'), ''),
              coalesce(rp.phone)]                                                           as customer_info,
        cpcr.value_remind                                                                   as value_remind
    from current_partner_card_rank_by_period cpcr
        join res_partner rp on rp.id = cpcr.customer_id
        left join store_first_order sfo on sfo.customer_id = rp.id and sfo.brand_id = {self.brand_id.id}
        left join store st on st.id = sfo.store_id
        left join ngay_mua_gn_by_id nmgn on nmgn.pcr_id = cpcr.pcr_id
        join card_rank c_cr on c_cr.id = cpcr.current_rank_id
        join card_rank n_cr on n_cr.id = cpcr.new_cr_id
        join value_to_upper_by_customer vtu on vtu.pcr_id = cpcr.pcr_id
)
select *, row_number() over () as num
from data_final
where value_remind <= dt_ps
order by num
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Sắp lên hạng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Sắp lên hạng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Đến ngày %s' % self.to_date.strftime('%d/%m/%Y'), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('store_name'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('customer_info')[0], formats.get('normal_format'))
            sheet.write(row, 3, value.get('customer_info')[1], formats.get('normal_format'))
            sheet.write(row, 4, value.get('customer_info')[2], formats.get('normal_format'))
            sheet.write(row, 5, value.get('customer_info')[3], formats.get('normal_format'))
            sheet.write(row, 7, value.get('ngay_mua_dk'), formats.get('center_format'))
            sheet.write(row, 8, value.get('ngay_mua_gn'), formats.get('center_format'))
            sheet.write(row, 8, value.get('ngay_ck'), formats.get('center_format'))
            sheet.write(row, 9, value.get('dt_ps', 0), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('min_turnover', 0) - value.get('dt_ps', 0), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('current_rank'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('new_rank'), formats.get('normal_format'))
            row += 1
