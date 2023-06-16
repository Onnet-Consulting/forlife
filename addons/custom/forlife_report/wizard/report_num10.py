# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError

TITLES = [
    'STT', 'Cửa hàng', 'Mã khách', 'Tên khách hàng', 'Giới tính', 'Ngày sinh', 'Điện thoại', 'Ngày mua đầu kỳ',
    'Ngày mua gần nhất', 'DT mua hàng', 'Hạng hiện tại', 'Hạng mới', 'Ngày lên hạng', 'Thực hiện', 'Ngày thực hiện'
]


class ReportNum10(models.TransientModel):
    _name = 'report.num10'
    _inherit = 'report.base'
    _description = 'Up Rank History'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    from_rank_id = fields.Many2one('card.rank', string='From rank')
    to_rank_id = fields.Many2one('card.rank', string='To rank')
    store_ids = fields.Many2many('store', string='Store')
    customer_ids = fields.Many2many('res.partner', string='Customer', domain=lambda self: [('group_id', 'in', self.env['res.partner.group'].search([('code', '=', 'C')]).ids)])

    @api.constrains('from_date', 'to_date')
    def validate_params(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        conditions = ''
        conditions += f"and pcrl.old_card_rank_id = {self.from_rank_id.id}\n" if self.from_rank_id else ''
        conditions += f"and pcrl.new_card_rank_id = {self.to_rank_id.id}\n" if self.to_rank_id else ''
        conditions += f"and pcr.customer_id = any (array{self.customer_ids.ids})\n" if self.customer_ids else ''
        conditions += '' if not self.store_ids else f"""
and (select coalesce(name, '')
     from store where id = (
        select store_id from store_first_order
         where customer_id = rp.id and brand_id = {self.brand_id.id}
         limit 1
        )
    ) = any (array{self.store_ids.mapped('name')})
"""
        query = f"""
select
    row_number() over (order by pcrl.order_date desc)                                  as num,
    (select coalesce(name, '')
     from store where id = (
        select store_id from store_first_order
         where customer_id = rp.id and brand_id = {self.brand_id.id}
         limit 1
        )
    )                                                                                  as store_name,
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
          case when rp.gender = 'male' then 'Nam' when rp.gender = 'female' then 'Nữ' when rp.gender = 'other' then 'Khác' else '' end ,
          coalesce(to_char(rp.birthday + ({tz_offset} || ' h')::interval, 'DD/MM/YYYY'), ''),
          coalesce(rp.phone)]                                                           as customer_info
from partner_card_rank_line pcrl
    join partner_card_rank pcr on pcr.id = pcrl.partner_card_rank_id
    join res_partner rp on rp.id = pcr.customer_id
where pcr.brand_id = {self.brand_id.id}
    and pcrl.old_card_rank_id <> pcrl.new_card_rank_id
    and {format_date_query("pcrl.order_date", tz_offset)} between '{self.from_date}' and '{self.to_date}'
{conditions}
order by num
        """
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Lịch sử nâng hạng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Lịch sử nâng hạng', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
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
            sheet.write(row, 6, value.get('customer_info')[4], formats.get('normal_format'))
            sheet.write(row, 7, value.get('ngay_mua_dk'), formats.get('center_format'))
            sheet.write(row, 8, value.get('ngay_mua_gn'), formats.get('center_format'))
            sheet.write(row, 9, value.get('dt_mua', 0), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('current_rank'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('new_rank'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('date_up_rank'), formats.get('center_format'))
            sheet.write(row, 13, value.get('implementation'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('date_implementation'), formats.get('center_format'))
            row += 1
