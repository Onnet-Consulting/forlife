# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'STT', 'Ngày', 'Mã cửa hàng', 'Tên cửa hàng', 'Số chứng từ gốc', 'Nội dung',
    'Số tiền nộp', 'Số tiền thu', 'Tiền chênh lệch', 'Số CT chênh lệch', 'Trạng thái'
]


class ReportNum44(models.TransientModel):
    _name = 'report.num44'
    _inherit = 'report.base'
    _description = 'Báo cáo chênh lệch tiền nộp về công ty'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_ids = fields.Many2many('store', string='Store')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand_id(self):
        self.store_ids = self.store_ids.filtered(lambda f: f.brand_id.id == self.brand_id.id)

    def _get_query(self, allowed_company, store_ids):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        sql = f"""
with state_json as (select json_object_agg(xx.value, coalesce(xx.name::json ->> '{user_lang_code}', xx.name::json ->> 'en_US')) as data
                    from ir_model_fields_selection xx
                             join ir_model_fields cc on cc.id = xx.field_id and cc.name = 'state' and cc.model = 'account.move'),
     du_lieu_ct_goc as (select am.id                            as move_id,
                               am.date                          as ngay,
                               st.code                          as ma_ch,
                               st.name                          as ten_ch,
                               am.name                          as so_ct_goc,
                               aml.name                         as noi_dung,
                               am.pos_orig_amount               as so_tien_nop,
                               coalesce(aml.amount_currency, 0) as so_tien_thu1
                        from account_move am
                                 left join pos_session ps on am.pos_trans_session_id = ps.id
                                 left join pos_config pc on ps.config_id = pc.id
                                 left join store st on st.id = pc.store_id
                                 left join account_move_line aml on aml.move_id = am.id
                                 join account_account aa on aa.id = aml.account_id and aa.account_type = 'asset_cash'
                        where pos_orig_amount > 0 
                        and {format_date_query("am.date", tz_offset)} between '{self.from_date}' and '{self.to_date}' 
                        and st.brand_id = {self.brand_id.id}
                        and st.id = any(array{store_ids})
                        and am.date between '{self.from_date}' and '{self.to_date}'),
     du_lieu_ct_chenh_lech as (select am.id                                             as move_id,
                                      am2.name                                          as so_ct_chenh_lech,
                                      aml.amount_currency                               as so_tien_thu2,
                                      (select data::json ->> am2.state from state_json) as trang_thai
                               from account_move am
                                        left join account_move am2 on am.pos_trans_diff_move_id = am2.id and am2.state <> 'cancel'
                                        left join account_move_line aml on aml.move_id = am2.id
                                        join account_account aa on aa.id = aml.account_id and aa.account_type = 'asset_cash'
                               where am.id in (select distinct move_id from du_lieu_ct_goc))
select row_number() over (order by tb1.move_id)                             as stt,
       to_char(tb1.ngay, 'DD/MM/YYYY')                                      as ngay,
       tb1.ma_ch,
       tb1.ten_ch,
       tb1.so_ct_goc,
       tb1.noi_dung,
       tb1.so_tien_nop,
       tb1.so_tien_thu1 + coalesce(tb2.so_tien_thu2, 0)                     as so_tien_thu,
       tb1.so_tien_nop - (tb1.so_tien_thu1 + coalesce(tb2.so_tien_thu2, 0)) as tien_chenh_lech,
       coalesce(tb2.so_ct_chenh_lech, '')                                   as so_ct_chenh_lech,
       coalesce(tb2.trang_thai, '')                                         as trang_thai
from du_lieu_ct_goc tb1
         left join du_lieu_ct_chenh_lech tb2 on tb1.move_id = tb2.move_id
order by stt
        """
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        Store = self.env['store'].with_context(report_ctx='report.num44,store')
        store_ids = self.store_ids.ids if self.store_ids else (Store.search([('brand_id', '=', self.brand_id.id)]).ids or [-1])
        query = self._get_query(allowed_company, store_ids)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo chênh lệch tiền nộp về công ty')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo chênh lệch tiền nộp về công ty', formats.get('header_format'))
        sheet.write(2, 0, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        sheet.write(2, 2, f'Thương hiệu: {self.brand_id.name}', formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ma_ch'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ten_ch'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('so_ct_goc'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('noi_dung'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('so_tien_nop'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('so_tien_thu'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('tien_chenh_lech'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('so_ct_chenh_lech'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('trang_thai'), formats.get('normal_format'))
            row += 1
