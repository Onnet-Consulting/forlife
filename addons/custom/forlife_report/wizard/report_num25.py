# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_report.wizard.report_base import format_date_query
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

TITLES = [
    'STT', 'KHU VỰC', 'MÃ CỬA HÀNG', 'TÊN CỬA HÀNG', 'MÃ NHÂN VIÊN', 'TÊN NHÂN VIÊN', 'VỊ TRÍ', 'VỊ TRÍ KIÊM NHIỆM',
    'SỐ BILL', 'TB BILL', 'TỔNG CỘNG', 'MỤC TIÊU CÁ NHÂN', 'MỤC TIÊU CỬA HÀNG', 'THU NHẬP DỰ TÍNH'
]


class ReportNum25(models.TransientModel):
    _name = 'report.num25'
    _inherit = 'report.base'
    _description = 'Báo cáo dự tính thu nhập nhân viên bán hàng theo doanh thu'

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    bo_plan_id = fields.Many2one('business.objective.plan', string='BO Plan', required=True)
    store_ids = fields.Many2many('store', string='Store')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    sale_province_id = fields.Many2one('res.sale.province', 'Sale Province')
    view_type = fields.Selection([('by_day', 'By day'), ('by_month', 'By month')], string='View type', required=True, default='by_day')

    @api.constrains('from_date', 'to_date', 'bo_plan_id')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))
            bo_plan_id = record.bo_plan_id
            if record.from_date and record.to_date and bo_plan_id and (record.from_date < bo_plan_id.from_date or record.to_date > bo_plan_id.to_date):
                raise ValidationError(_("Date must be between '%s' and '%s'") % (bo_plan_id.from_date.strftime('%d/%m/%Y'), bo_plan_id.to_date.strftime('%d/%m/%Y')))

    @api.onchange('brand_id')
    def onchange_brand(self):
        self.store_ids = False
        self.bo_plan_id = False

    @api.onchange('bo_plan_id')
    def onchange_bo_plan(self):
        self.from_date = self.bo_plan_id.from_date
        self.to_date = self.bo_plan_id.to_date

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        employee_conditions = '' if not self.employee_id else f'and employee_id = {self.employee_id.id}'
        store_conditions = f'''and pc.store_id = any(array{self.store_ids.ids if self.store_ids else (
                self.env['store'].with_context(report_ctx='report.num11,store').search([('brand_id', '=', self.brand_id.id)]).ids or [-1])})'''
        sale_province_conditions = f"where rsp.id = {self.sale_province_id.id}" if self.sale_province_id else ''

        sql = f"""
select (
    with orders as (select po.id                                            as id,
                           pc.store_id                                      as store_id,
                           (po.date_order + interval '{tz_offset} h')::date as date_order
                    from pos_order po
                             left join pos_session ps on po.session_id = ps.id
                             left join pos_config pc on ps.config_id = pc.id
                    where po.brand_id = {self.brand_id.id} {store_conditions}
                      and {format_date_query("po.date_order", tz_offset)}
                        between '{self.from_date}' and '{self.to_date}'),
         order_lines as (select pol.id,
                                pol.order_id,
                                po.store_id,
                                pol.employee_id,
                                (pol.qty * pol.original_price
                                        - coalesce((select sum((case
                                                        when disc.type = 'point' then disc.recipe * 1000
                                                        when disc.type = 'ctkm' then disc.discounted_amount
                                                        else disc.recipe end))::float
                                        from pos_order_line_discount_details disc
                                        where disc.pos_order_line_id = pol.id
                                        group by disc.pos_order_line_id), 0))::float4 as total,
                                to_char(po.date_order, 'DD/MM/YYYY')  as by_day,
                                to_char(po.date_order, 'MM/YYYY')     as by_month
                         from pos_order_line pol
                                  join orders po on po.id = pol.order_id
                                  left join product_product pp on pp.id = pol.product_id
                                  left join product_template pt on pt.id = pp.product_tmpl_id
                         where pt.detailed_type <> 'service'
                           and (pt.voucher = false or pt.voucher is null)),
         employee_target as (select store_id,
                                    employee_id,
                                    job_id,
                                    concurrent_position_id,
                                    revenue_target
                             from business_objective_employee
                             where bo_plan_id = {self.bo_plan_id.id}
                             {employee_conditions}
                             {f'and store_id = any(array{self.store_ids.ids})' if self.store_ids else ''}),
         store_target as (select store_id,
                                 revenue_target
                          from business_objective_store
                          where bo_plan_id = {self.bo_plan_id.id}),
         data_group_details as (select store_id,
                                      employee_id,
                                      json_object_agg({self.view_type}, total) as detail
                               from (select store_id,
                                            employee_id,
                                            {self.view_type},
                                            sum(coalesce(total, 0)) as total
                                     from order_lines
                                     group by store_id, employee_id, {self.view_type}) as xx
                               group by store_id, employee_id),
         data_groups as (select eta.store_id                        as store_id,
                                eta.employee_id                     as employee_id,
                                eta.job_id                          as job_id,
                                eta.concurrent_position_id          as concurrent_position_id,
                                sta.revenue_target                  as muc_tieu_cua_hang,
                                eta.revenue_target                  as muc_tieu_ca_nhan,
                                array_agg(distinct pol.order_id)    as count_order,
                                sum(coalesce(pol.total, 0))::float4 as total
                         from employee_target eta
                                  left join store_target sta on eta.store_id = sta.store_id
                                  left join order_lines pol on eta.store_id = pol.store_id
                             and eta.employee_id = pol.employee_id
                         group by eta.store_id,
                                  eta.employee_id,
                                  eta.job_id,
                                  eta.concurrent_position_id,
                                  sta.revenue_target,
                                  eta.revenue_target),
        data_group_stores as (select dg.store_id                                  as store_id,
                                  sum(dg.total)                                   as total,
                                  coalesce(sum(cr.fixed_coefficient_indirect), 0) as total_fixed_coefficient_indirect
                           from data_groups dg
                           left join coefficient_revenue cr on cr.job_id = coalesce(dg.concurrent_position_id, dg.job_id)
                            and cr.brand_id = {self.brand_id.id}
                           group by store_id),
        final_data as (select row_number() over (order by dg.employee_id)      as stt,
                           rsp.name                                            as khu_vuc,
                           s.code                                              as ma_cua_hang,
                           s.name                                              as ten_cua_hang,
                           he.code                                             as ma_nhan_vien,
                           he.name                                             as ten_nhan_vien,
                           coalesce(job1.name::json ->> '{user_lang_code}', job1.name::json ->> 'en_US') as vi_tri,
                           coalesce(job2.name::json ->> '{user_lang_code}', job2.name::json ->> 'en_US') as vi_tri_kiem_nhiem,
                           array_length(dg.count_order, 1)                     as so_bill,
                           (dg.total / array_length(dg.count_order, 1))::float as tb_bill,
                           dg.total::float                                     as tong_cong,
                           dgs.total::float                                    as tong_cong_cua_hang,
                           dgs.total_fixed_coefficient_indirect::float         as tong_hs_vt_gt,
                           dg.muc_tieu_ca_nhan                                 as muc_tieu_ca_nhan,
                           dg.muc_tieu_cua_hang                                as muc_tieu_cua_hang,
                           dgd.detail                                          as detail,
                           coalesce(dg.concurrent_position_id, dg.job_id)      as job_id,
                           case
                               when coalesce(dg.muc_tieu_ca_nhan, 0) > 0
                                   then (dg.total / dg.muc_tieu_ca_nhan * 100)::float
                               else 0 end                                      as pt_ht_canhan,
                           case
                               when coalesce(dg.muc_tieu_cua_hang, 0) > 0
                                   then (dgs.total / dg.muc_tieu_cua_hang * 100)::float
                               else 0 end                                      as pt_ht_cuahang
                    from data_groups dg
                             left join data_group_details dgd on dg.store_id = dgd.store_id and dg.employee_id = dgd.employee_id
                             left join data_group_stores dgs on dgs.store_id = dg.store_id
                             left join store s on s.id = dg.store_id
                             left join stock_warehouse wh on wh.id = s.warehouse_id
                             left join res_sale_province rsp on rsp.id = wh.sale_province_id
                             left join hr_job job1 on job1.id = dg.job_id
                             left join hr_job job2 on job2.id = dg.concurrent_position_id
                             left join hr_employee he on he.id = dg.employee_id
                    {sale_province_conditions}
                    order by stt)
"""
        sql += f"""
    select json_agg(final_data.*)
        from final_data)                 as data,
    (select json_object_agg(vi_tri, pt_nhan_vien) as data
        from (select vi_tri, json_object_agg(pt_nhan_vien, tile_tructiep) as pt_nhan_vien
              from (select cr.job_id                                           as vi_tri,
                           pcbe.percentage                                     as pt_nhan_vien,
                           json_object_agg(pcbt.percentage, pcbt.ratio::float) as tile_tructiep
                    from coefficient_revenue cr
                             join percentage_complete_by_employee pcbe on cr.id = pcbe.coefficient_revenue_id
                             join percentage_complete_by_store pcbt on pcbe.id = pcbt.pc_by_employee_id
                    where cr.brand_id = {self.brand_id.id}
                    group by cr.job_id, pcbe.percentage) as x1
              group by vi_tri) as x2)    as tile_tructiep,

    (select json_object_agg(vi_tri, tile_giantiep) as data
        from (select cr.job_id                                           as vi_tri,
                     json_object_agg(pcbt.percentage, pcbt.ratio::float) as tile_giantiep
              from coefficient_revenue cr
                       join percentage_complete_by_store pcbt on cr.id = pcbt.coefficient_revenue_id
              where cr.brand_id = {self.brand_id.id}
              group by cr.job_id) as xx) as tile_giantiep,
    (select json_object_agg(job_id, array[fixed_coefficient_direct::float, fixed_coefficient_indirect::float])
        from coefficient_revenue where brand_id = {self.brand_id.id}) as he_so_co_dinh
"""
        return sql

    def get_title_with_view_type(self, from_date, to_date, view_type):
        format_date, day, month = ('%d/%m/%Y', 1, 0) if view_type == 'by_day' else ('%m/%Y', 0, 1)
        title = []
        while from_date <= to_date:
            title.append(from_date.strftime(format_date))
            from_date = from_date + relativedelta(months=month, days=day)
        if to_date.strftime(format_date) not in title:
            title.append(to_date.strftime(format_date))
        return title

    def format_data(self, data):
        _data = data and data[0] or {}
        res = []
        column_add = self.get_title_with_view_type(self.from_date, self.to_date, self.view_type)
        tile_tructiep = _data.get('tile_tructiep') or {}
        tile_giantiep = _data.get('tile_giantiep') or {}
        he_so_co_dinh = _data.get('he_so_co_dinh') or {}
        for value in (_data.get('data') or []):
            qty_by_time = value.pop('detail') or {}
            for c in column_add:
                value[c] = qty_by_time.get(c, 0) or 0

            # Tổng hợp thu nhập dự tính
            job_id = value.get('job_id')
            pt_ht_canhan = value.get('pt_ht_canhan') or 0
            pt_ht_cuahang = value.get('pt_ht_cuahang') or 0
            if job_id is not None:
                # kiểm tra hệ số
                _heso_codinh = he_so_co_dinh.get(str(job_id)) or [0, 0]
                _heso_codinh_tructiep = _heso_codinh[0]
                _heso_codinh_giantiep = _heso_codinh[1]

                # Thu nhập theo hệ số trực tiếp
                if _heso_codinh_tructiep != 0:
                    thu_nhap_du_tinh_truc_tiep = value.get('tong_cong', 0) * _heso_codinh_tructiep / 100
                else:
                    pt_ht_canhan_tructiep = tile_tructiep.get(str(job_id)) or {}
                    phantram_hoanthanh = 0
                    phantram_hoanthanh_str = ''
                    for k in pt_ht_canhan_tructiep.keys():
                        _phantram_hoanthanh = float(k)
                        if _phantram_hoanthanh <= pt_ht_canhan and _phantram_hoanthanh >= phantram_hoanthanh:
                            phantram_hoanthanh = _phantram_hoanthanh
                            phantram_hoanthanh_str = k
                    pt_ht_cuahang_tructiep = pt_ht_canhan_tructiep.get(phantram_hoanthanh_str) or {}
                    phantram_hoanthanh = 0
                    heso_tructiep = 0
                    for k, v in pt_ht_cuahang_tructiep.items():
                        _phantram_hoanthanh = float(k)
                        if _phantram_hoanthanh <= pt_ht_cuahang and _phantram_hoanthanh >= phantram_hoanthanh:
                            phantram_hoanthanh = _phantram_hoanthanh
                            heso_tructiep = v
                    thu_nhap_du_tinh_truc_tiep = value.get('tong_cong', 0) * heso_tructiep / 100

                # Thu nhập theo hệ số gián tiếp
                pt_ht_cuahang_giantiep = tile_giantiep.get(str(job_id)) or {}
                thu_nhap_du_tinh_gian_tiep = 0
                if pt_ht_cuahang_giantiep and value.get('tong_hs_vt_gt'):
                    phantram_hoanthanh = 0
                    heso_giantiep = 0
                    for k, v in pt_ht_cuahang_giantiep.items():
                        _phantram_hoanthanh = float(k)
                        if _phantram_hoanthanh <= pt_ht_cuahang and _phantram_hoanthanh >= phantram_hoanthanh:
                            phantram_hoanthanh = _phantram_hoanthanh
                            heso_giantiep = v
                    thu_nhap_du_tinh_gian_tiep = value.get('tong_cong_cua_hang', 0) / value.get('tong_hs_vt_gt') * heso_giantiep * _heso_codinh_giantiep / 100

                # Thu nhập dự tính
                value['thu_nhap_du_tinh'] = thu_nhap_du_tinh_truc_tiep + thu_nhap_du_tinh_gian_tiep

            res.append(value)
        return {
            'titles': TITLES + column_add,
            'data': res,
            'column_add': column_add,
        }

    def get_data(self, allowed_company):
        self.ensure_one()
        values = super().get_data(allowed_company)
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update(self.format_data(data))
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo dự tính thu nhập nhân viên')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo dự tính thu nhập nhân viên bán hàng theo doanh thu', formats.get('header_format'))
        sheet.write(2, 0, 'Thương hiệu: %s' % self.brand_id.name, formats.get('italic_format'))
        sheet.write(2, 2, 'Từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y')), formats.get('italic_format'))
        titles = data.get('titles') or []
        for idx, title in enumerate(titles):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(titles) - 1, 20)
        row = 5
        column_add = data.get('column_add')
        for value in data.get('data'):
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('khu_vuc'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ma_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ten_cua_hang'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('ma_nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('ten_nhan_vien'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('vi_tri'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('vi_tri_kiem_nhiem'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('so_bill'), formats.get('int_number_format'))
            sheet.write(row, 9, value.get('tb_bill'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('tong_cong'), formats.get('int_number_format'))
            sheet.write(row, 11, value.get('muc_tieu_ca_nhan'), formats.get('int_number_format'))
            sheet.write(row, 12, value.get('muc_tieu_cua_hang'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('thu_nhap_du_tinh'), formats.get('int_number_format'))
            col = 14
            for c in column_add:
                sheet.write(row, col, value.get(c), formats.get('int_number_format'))
                col += 1
            row += 1
