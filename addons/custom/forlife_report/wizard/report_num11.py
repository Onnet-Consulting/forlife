# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Cửa hàng', 'Mã khách', 'Tên khách hàng', 'Ngày sinh', 'Điện thoại', 'Ngày mua đầu kỳ',
    'Ngày mua gần nhất', 'Ngày cuối kỳ', 'DT phát sinh', 'Giá trị cần đạt', 'Hạng hiện tại', 'Hạng mới',
]


class ReportNum11(models.TransientModel):
    _name = 'report.num11'
    _inherit = 'report.base'
    _description = 'Report about to rank up'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    to_date = fields.Date('To date', required=True)
    from_rank_id = fields.Many2one('card.rank', string='From rank')
    to_rank_id = fields.Many2one('card.rank', string='To rank')
    store_ids = fields.Many2many('store', string='Store')
    customer_ids = fields.Many2many('res.partner', string='Customer', domain=lambda self: [('group_id', 'in', self.env['res.partner.group'].search([('code', '=', 'C')]).ids)])

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False

    def view_report(self):
        self.ensure_one()
        action = self.env.ref('forlife_report.report_num_11_client_action').read()[0]
        return action

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        conditions = ''
        conditions += f"and pcrl.old_card_rank_id = {self.from_rank_id.id}\n" if self.from_rank_id else ''
        conditions += f"and pcrl.new_card_rank_id = {self.to_rank_id.id}\n" if self.to_rank_id else ''
        conditions += f"and pcr.customer_id = any (array{self.customer_ids.ids})\n" if self.customer_ids else ''
        conditions += '' if not self.store_ids else f"""
and pcrl.order_id in (
    select id from pos_order
        where date_order <= '{self.to_date}'
            and session_id in (
                select id from pos_session where config_id in (
                    select id from pos_config where store_id = any (array{self.store_ids.ids})))
)"""
        query = f"""
select
    (select coalesce(name, '')
     from store where id in (
        select store_id from pos_config where id in (
            select config_id from pos_session where id in (
                select session_id from pos_order where id = pcrl.order_id
            )
        )
    ))                                                                                  as store_name,
    (select to_char(order_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')
        from partner_card_rank_line
        where partner_card_rank_id = pcr.id and order_id notnull
             and order_date >= pcrl.order_date - ((
                select COALESCE(time_set_rank, 0) from member_card
                where id = pcrl.program_cr_id) || ' d')::interval
        order by order_date asc limit 1)                                                as ngay_mua_dk,
    (select to_char(order_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')
        from partner_card_rank_line
         where partner_card_rank_id = pcrl.partner_card_rank_id and order_id notnull
            and {format_date_query("order_date", tz_offset)} <= '{self.to_date}'
         order by order_date desc limit 1)                                              as ngay_mua_gn,
    coalesce(pcrl.value_up_rank, 0)                                                     as dt_mua,
    (select name from card_rank where id = pcrl.old_card_rank_id)                       as current_rank,
    (select name from card_rank where id = pcrl.new_card_rank_id)                       as new_rank,
    to_char(pcrl.order_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')            as date_up_rank,
    to_char(pcrl.real_date + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY')             as date_implementation,
    case when pcrl.order_id notnull then 'Auto' else '' end                             as implementation,
    array[coalesce(rp.internal_code, ''),
          coalesce(rp.name, ''),
          coalesce(to_char(rp.birthday + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY'), ''),
          coalesce(rp.phone)]                                                           as customer_info
from partner_card_rank_line pcrl
    join partner_card_rank pcr on pcr.id = pcrl.partner_card_rank_id
    join res_partner rp on rp.id = pcr.customer_id
where pcr.brand_id = {self.brand_id.id}
    and pcrl.old_card_rank_id <> pcrl.new_card_rank_id
    and {format_date_query("pcrl.order_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
{conditions}
order by pcrl.order_date desc
        """
        return query

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        return {
            'reportTitle': self.name,
            'titles': TITLES,
            "data": data,
        }
