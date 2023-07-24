# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TITLE_LAYER1 = ['STT', 'Chi nhánh', 'Ngày', 'Phiên bán hàng', 'POS', 'Tổng tiền thu', 'Tổng tiền chi']
TITLE_LAYER2 = ['STT', 'Ngày', 'Phiên bán hàng', 'Số CT', 'Nội dung', 'Khoản mục', 'TK nợ', 'TK có', 'Số tiền thu', 'Số tiền chi', 'Tên NV', 'Mã NV']


class ReportNum22(models.TransientModel):
    _name = 'report.num22'
    _inherit = ['report.base', 'export.excel.client']
    _description = 'Cash receipts report'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    store_ids = fields.Many2many('store', string='Store')
    so_ct = fields.Char(string='Number CT')
    type = fields.Selection([('all', _('All')), ('revenue', _('Revenue')), ('expenditure', _('Expenditure'))], 'Type', default='all', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = self.store_ids.filtered(lambda f: f.brand_id == self.brand_id)

    def _get_query(self):
        self.ensure_one()

        type_x = {
            'all': '',
            'revenue': 'and absl1.amount > 0',
            'expenditure': 'and absl1.amount < 0',
        }

        query = f"""
with data_filtered as (
    select
        absl1.id    as statement_line_id,
        ps.id       as session_id,
        am.id       as move_id,
        pc.id       as config_id,
        store.id    as store_id
    from account_bank_statement_line absl1
        join account_move am on absl1.id = am.statement_line_id
        join pos_session ps on absl1.pos_session_id = ps.id
        left join pos_config pc on ps.config_id = pc.id
        left join store on pc.store_id = store.id
    where am.date between '{self.from_date}' and '{self.to_date}'
    and {('store.id = any(array%s)' % self.store_ids.ids) if self.store_ids else ('store.brand_id = %s' % self.brand_id.id)}
    {type_x.get(self.type) or ''}
    {"and am.name ilike '%{}%'".format(self.so_ct) if self.so_ct else ''}
),
tai_khoan_co as (
    select
        aml1.move_id as move_id,
        aa1.code     as tk_co
    from account_move_line aml1
        join account_account aa1 on aml1.account_id = aa1.id
    where aml1.credit > 0 and aml1.move_id in (select move_id from data_filtered)
),
tai_khoan_no as (
    select
        aml2.move_id as move_id,
        aa2.code     as tk_no
    from account_move_line aml2
        join account_account aa2 on aml2.account_id = aa2.id
    where aml2.debit > 0 and aml2.move_id in (select move_id from data_filtered)
),
tai_khoan as (
    select
        coalesce(tkc.move_id, tkn.move_id) as move_id,
        tkc.tk_co as tk_co,
        tkn.tk_no as tk_no
    from tai_khoan_co tkc
    full outer join tai_khoan_no tkn on tkc.move_id = tkn.move_id
),
data_details as (
    select
        row_number() over (PARTITION BY ps2.id order by am2.date desc) as num,
        concat(to_char(am2.date, 'DDMMYYYY') || ps2.id::text)   as key,
        s.name                                                  as chi_nhanh,
        to_char(am2.date, 'DD/MM/YYYY')                         as ngay,
        ps2.name                                                as phien_bh,
        pc2.name                                                as pos,
        am2.name                                                as so_ct,
        absl2.reason                                            as noi_dung,
        pel.name                                                as khoan_muc,
        tk.tk_no                                                as tk_no,
        tk.tk_co                                                as tk_co,
        greatest(absl2.amount, 0)::float                        as tien_thu,
        abs(least(absl2.amount, 0))::float                      as tien_chi,
        coalesce(he.name, rp.name)                              as ten_nv,
        he.code                                                 as ma_nv
    from account_bank_statement_line absl2
        join account_move am2 on absl2.id = am2.statement_line_id
        left join tai_khoan tk on tk.move_id = absl2.move_id
        join data_filtered df on df.statement_line_id = absl2.id
        left join pos_session ps2 on ps2.id = df.session_id
        left join pos_config pc2 on pc2.id = df.config_id
        left join store s on s.id = df.store_id
        join res_users ru on absl2.create_uid = ru.id
        left join hr_employee he on ru.id = he.user_id
        left join res_partner rp on ru.partner_id = rp.id
        left join pos_expense_label pel on absl2.expense_label_id = pel.id
    order by num
),
tong_thu_chi as (
    select
        key,
        chi_nhanh,
        ngay,
        phien_bh,
        pos,
        sum(tien_thu) as tong_tien_thu,
        sum(tien_chi) as tong_tien_chi
    from data_details
    group by key, chi_nhanh, ngay, phien_bh, pos
),
gop_chi_tiet as (
    select
        key,
        array_agg(to_json(data_details.*)) as transaction_detail
    from data_details
    group by key
)
select
    row_number() over (order by ttc.key)    as num,
    ttc.*,
    gct.transaction_detail                  as transaction_detail
from tong_thu_chi ttc
    join gop_chi_tiet gct on gct.key = ttc.key
order by num
"""
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
