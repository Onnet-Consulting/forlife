# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TITLES = [
    'Stt', 'Ngày chứng từ', 'Số chứng từ', 'Mã đối tượng', 'Tên đối tượng', 'Diễn giải', 'Tk đối ứng', 'Phát sinh Nợ',
    'Phát sinh Có', 'Mã vụ việc', 'Bộ phận', 'Tên bộ phận', 'Khoản mục chi phí', 'Số lệnh sản xuất'
]


class ReportNum46(models.TransientModel):
    _name = 'report.num46'
    _inherit = 'report.base'
    _description = 'Sổ chi tiết tài khoản'

    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)
    partner_ids = fields.Many2many('res.partner', 'partner_report46_rel', string='Đối tượng')
    partner_count = fields.Integer('Partner count', compute='_compute_value')
    ref_no = fields.Char(string='Số chứng từ')
    account_ids = fields.Many2many('account.account', 'account_report46_rel', string='TK đối ứng')
    account_count = fields.Integer('Account count', compute='_compute_value')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.depends('partner_ids', 'account_ids')
    def _compute_value(self):
        for line in self:
            line.partner_count = len(line.partner_ids)
            line.account_count = len(line.account_ids)

    def btn_choice_values(self):
        action = self.env["ir.actions.actions"]._for_xml_id(f"forlife_report.{self._context.get('action_xml_id')}")
        action['res_id'] = self.id
        action['context'] = self._context
        return action

    def print_xlsx(self):
        self.check_allowed_company()
        return super().print_xlsx()

    def view_report(self):
        self.check_allowed_company()
        return super().view_report()

    def check_allowed_company(self):
        allowed_company = len(self._context.get('allowed_company_ids', []))
        if allowed_company > 1:
            raise ValidationError(f'Không thể thực hiện xem báo cáo này trên {allowed_company} công ty khác nhau')

    def _get_query(self, allowed_company):
        self.ensure_one()

        sql = f"""
with account_move_lines as (select id,
                                   move_id,
                                   product_id,
                                   expense_item_id
                            from account_move_line
                            where date between '{self.from_date}' and '{self.to_date}'
                              and company_id = {allowed_company}
                              {f"and move_name ilike '%%{self.ref_no}%%'" if self.ref_no else ''}
                              {f"and partner_id = any (array {self.partner_ids.ids})" if self.partner_ids else ''}
                              {f"and account_id = any (array {self.account_ids.ids})" if self.account_ids else ''}
                            order by date desc, move_id desc),
     get_expense_item_by_id as (select json_object_agg(id, name) as value
                                from expense_item
                                where company_id = {allowed_company}),
     get_expense_item_by_code as (select json_object_agg(code, name) as value
                                  from expense_item
                                  where company_id = {allowed_company}),
     barcode_by_product_id as (select json_object_agg(id, substring(coalesce(barcode, '') from 2)) as barcode
                               from product_product
                               where id in (select distinct product_id
                                            from account_move_lines
                                            where product_id notnull)),
     aml_has_expense_item as (select id,
                                     (select value::json ->> expense_item_id::text
                                      from get_expense_item_by_id) as expense_name
                              from account_move_lines
                              where expense_item_id notnull),
     aml_miss_expense_item1 as (select aml.id,
                                       aml.move_id,
                                       (select value::json ->> (select barcode::json ->> aml.product_id::text
                                                                from barcode_by_product_id)
                                        from get_expense_item_by_code) as expense_name
                                from account_move_lines aml
                                where aml.expense_item_id isnull
                                  and aml.product_id notnull),
     aml_miss_expense_item2 as (select x1.id,
                                       (select value::json ->> sl.expense_item_id::text
                                        from get_expense_item_by_id) as expense_name
                                from account_move am
                                         join aml_miss_expense_item1 x1 on x1.move_id = am.id
                                         join stock_move sm on sm.id = am.stock_move_id
                                         join stock_picking sp on sp.id = sm.picking_id
                                         join stock_location sl on sl.id = sp.location_dest_id
                                where x1.expense_name isnull
                                  and sp.other_export = true
                                  and sl.expense_item_id notnull),
     aml_expense_items as (select json_object_agg(x2.id, x2.expense_name) as data_expense_items
                           from (select id, expense_name
                                 from aml_has_expense_item
                                 union all
                                 select id, expense_name
                                 from aml_miss_expense_item1
                                 where expense_name notnull
                                 union all
                                 select id, expense_name
                                 from aml_miss_expense_item2) as x2)

select row_number() over (order by aml.move_id desc, aml.debit desc)             as stt,
       to_char(aml.date, 'DD/MM/YYYY')                                           as ngay_ct,
       aml.move_name                                                             as so_ct,
       rp.ref                                                                    as ma_dt,
       rp.name                                                                   as ten_dt,
       aml.name                                                                  as dien_giai,
       aa.code                                                                   as tk_doi_ung,
       aml.debit                                                                 as ps_no,
       aml.credit                                                                as ps_co,
       oc.name                                                                   as ma_vv,
       aaa.code                                                                  as ma_bp,
       aaa.internal_name                                                         as ten_bp,
       (select data_expense_items::json ->> aml.id::text from aml_expense_items) as expense_item,
       fp.code                                                                   as so_lsx
from account_move_line aml
         left join res_partner rp on aml.partner_id = rp.id
         left join account_account aa on aml.account_id = aa.id
         left join occasion_code oc on aml.occasion_code_id = oc.id
         left join account_analytic_account aaa on aml.analytic_account_id = aaa.id
         left join forlife_production fp on aml.work_order = fp.id
where aml.id in (select id from account_move_lines)
"""
        return sql

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query(allowed_company and allowed_company[0] or -1)
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Sổ chi tiết tài khoản')
        sheet.set_row(3, 25)
        sheet.set_row(6, 25)
        sheet.freeze_panes(7, 0)
        sheet.write(0, 0, f'Công ty: {self.env.company.name or ""}', formats.get('bold_format_left'))
        sheet.write(1, 0, f'Địa chỉ: {self.env.company.street or ""}', formats.get('bold_format_left'))
        sheet.merge_range(3, 0, 3, len(data.get('titles')) - 1, 'Sổ chi tiết tài khoản', formats.get('header_format'))
        sheet.merge_range(4, 0, 4, len(data.get('titles')) - 1, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(6, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(TITLES) - 1, 20)
        row = 7
        for value in data.get('data'):
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay_ct'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('so_ct'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_dt'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ten_dt'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('dien_giai'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('tk_doi_ung'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('ps_no'), formats.get('int_number_format'))
            sheet.write(row, 8, value.get('ps_co'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('ma_vv'), formats.get('normal_format'))
            sheet.write(row, 10, value.get('ma_bp'), formats.get('normal_format'))
            sheet.write(row, 11, value.get('ten_bp'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('khoan_muc_cp'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('so_lsx'), formats.get('normal_format'))
            row += 1

        sheet.merge_range(row + 2, 1, row + 2, 2, 'Kế toán ghi sổ', formats.get('bold_format_center'))
        sheet.merge_range(row + 3, 1, row + 3, 2, '(Ký, họ tên)', formats.get('italic_format'))
        sheet.merge_range(row + 1, len(TITLES) - 2, row + 1, len(TITLES) - 1, '........Ngày.....tháng.....năm........', formats.get('italic_format'))
        sheet.merge_range(row + 2, len(TITLES) - 2, row + 2, len(TITLES) - 1, 'Kế toán trưởng', formats.get('bold_format_center'))
        sheet.merge_range(row + 3, len(TITLES) - 2, row + 3, len(TITLES) - 1, '(Ký, họ tên)', formats.get('italic_format'))

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        bold_format_center = {
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
        }
        bold_format_left = {
            'bold': 1,
            'align': 'left',
            'valign': 'vcenter',
        }
        bold_format_center = workbook.add_format(bold_format_center)
        bold_format_left = workbook.add_format(bold_format_left)
        res.get('header_format').set_align('center')
        res.get('italic_format').set_align('center')
        res.update({
            'bold_format_center': bold_format_center,
            'bold_format_left': bold_format_left
        })
        return res
