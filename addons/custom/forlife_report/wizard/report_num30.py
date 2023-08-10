# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import copy

TITLES = [
    'STT', 'Kho', 'Địa điểm', 'Mã SP', 'Tên SP', 'Đơn vị', 'Số lượng bán', 'Số lượng trả', 'Số lượng', 'Đơn giá', 'Thuế suất',
    'Thuế GTGT', 'Doanh thu bán hàng', 'Giảm trừ doanh thu', 'Khuyến mại bán hàng', 'Tổng thanh toán', 'Kênh bán'
]


class ReportNum30(models.TransientModel):
    _name = 'report.num30'
    _inherit = 'report.base'
    _description = 'Bảng kê hàng hóa xuất hóa đơn'

    @api.model
    def _get_default_year(self):
        return fields.Date.today().year

    @api.model
    def _get_default_month(self):
        return self.env['month.data'].search([('code', '=', str(fields.Date.today().month))])

    month = fields.Many2one('month.data', 'Month', required=True, default=_get_default_month)
    year = fields.Integer('Year', required=True, default=_get_default_year)
    product_count = fields.Integer('Product count', compute='_compute_value')
    product_ids = fields.Many2many('product.product', string='Products',
                                   domain="['|', ('detailed_type', '=', 'product'), '&', ('detailed_type', '=', 'service'), ('voucher', '=', True)]")
    warehouse_type_id = fields.Many2one('stock.warehouse.type', string='Warehouses Type', required=True)
    warehouse_count = fields.Integer('Warehouse count', compute='_compute_value')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    is_get_price_unit = fields.Boolean('Get Price Unit', default=True)
    is_with_tax = fields.Boolean('With tax', default=True)
    is_pos_order = fields.Boolean('Pos Order', default=True)
    is_wholesale = fields.Boolean('Wholesale', default=False)
    is_ecommerce = fields.Boolean('Ecommerce', default=False)
    is_inter_company = fields.Boolean('Inter-company', default=False)

    @api.depends('product_ids', 'warehouse_ids')
    def _compute_value(self):
        for line in self:
            line.product_count = len(line.product_ids)
            line.warehouse_count = len(line.warehouse_ids)

    def btn_choice_values(self):
        action = self.env["ir.actions.actions"]._for_xml_id(f"forlife_report.{self._context.get('action_xml_id')}")
        action['res_id'] = self.id
        action['context'] = self._context
        return action

    @api.onchange('warehouse_type_id')
    def onchange_warehouse_type_id(self):
        self.warehouse_ids = self.warehouse_ids.filtered(lambda f: f.whs_type.id == self.warehouse_type_id.id)

    @api.constrains('year')
    def check_year(self):
        for record in self:
            if record.year == 0:
                raise ValidationError('Năm không hợp lệ')

    def _get_query(self):
        self.ensure_one()
        tz_offset = self.tz_offset
        query = f"""
with order_lines as (select pol.id                    as order_line_id,
                            po.id                     as order_id,
                            pol.qty                   as qty,
                            coalesce(at.amount, 0)    as tax_percent,
                            pol.refunded_orderline_id as refunded_orderline_id,
                            pol.product_id            as product_id,
                            org_po.id                 as origin_order_id
                     from pos_order po
                              join pos_order_line pol on po.id = pol.order_id
                              join pos_session ps on ps.id = po.session_id
                              join pos_config pc on pc.id = ps.config_id
                              join store s on s.id = pc.store_id and s.warehouse_id = any (array {self.warehouse_ids.ids})
                              join product_product pp on pp.id = pol.product_id {f'and pp.id = any (array {self.product_ids.ids})' if self.product_ids else ''}
                              join product_template pt on pt.id = pp.product_tmpl_id
                              left join account_tax_pos_order_line_rel tax_rel on tax_rel.pos_order_line_id = pol.id
                              left join account_tax at on at.id = tax_rel.account_tax_id
                              left join pos_order_line org_pol on org_pol.id = pol.refunded_orderline_id
                              left join pos_order org_po on org_po.id = org_pol.order_id
                     where to_char(po.date_order + interval '{tz_offset} h', 'MM/YYYY') = '{"%.2d/%.4d" % (int(self.month.code), self.year)}'
                       and pol.is_promotion = any (array [false, null])
                       and pol.qty <> 0
                       and (pt.detailed_type = 'product' or (pt.detailed_type = 'service' and pt.voucher = true))),
     refunded_order_lines as (select pol.id                 as order_line_id,
                                     po.id                  as order_id,
                                     pol.qty                as qty,
                                     coalesce(at.amount, 0) as tax_percent,
                                     0                      as refunded_orderline_id,
                                     pol.product_id         as product_id,
                                     0                      as origin_order_id
                              from pos_order_line pol
                                       join pos_order po on po.id = pol.order_id
                                       left join account_tax_pos_order_line_rel tax_rel on tax_rel.pos_order_line_id = pol.id
                                       left join account_tax at on at.id = tax_rel.account_tax_id
                              where pol.id in (select distinct refunded_orderline_id
                                               from order_lines
                                               where refunded_orderline_id notnull
                                                 and refunded_orderline_id not in (select distinct order_line_id
                                                                                   from order_lines))),
     order_line_finals as (select *
                           from order_lines
                           union all
                           select *
                           from refunded_order_lines),
     discount_datas as ((select pos_order_line_id as order_line_id,
                                sum(
                                        case
                                            when type = any (array ['point', 'card']) then 0
                                            when type = 'ctkm' then discounted_amount
                                            else recipe
                                            end
                                    )             as giam_tru_dt,
                                sum(
                                        case
                                            when type = 'point' then recipe * 1000
                                            when type = 'ctkm' then discounted_amount
                                            else recipe
                                            end
                                    )             as khuyen_mai_bh
                         from pos_order_line_discount_details
                         where pos_order_line_id in (select distinct order_line_id from order_line_finals)
                         group by pos_order_line_id)),
     tong_thanh_toan as (select cl.id                 as order_line_id,
                                cl.incl_1 + cl.incl_2 as tong_tt
                         from (select pol1.id,
                                      pol1.price_subtotal_incl                   as incl_1,
                                      sum(coalesce(pol2.price_subtotal_incl, 0)) as incl_2
                               from pos_order_line pol1
                                        left join pos_order_line pol2 on pol1.id = pol2.product_src_id
                               where pol1.product_src_id is null
                                 and pol1.id in (select distinct order_line_id
                                                 from order_line_finals)
                               group by pol1.id, pol1.price_subtotal_incl) as cl),
     order_line_am as (select * from order_lines where qty < 0),
     order_line_duong as (select * from order_line_finals where qty > 0),
     location_info_am as (select ola.order_line_id, sl.id as location_id
                          from order_line_am ola
                                   left join stock_picking sp
                                             on sp.pos_order_id = ola.order_id
                                   left join stock_move sm on sm.picking_id = sp.id and sm.product_id = ola.product_id
                                   left join stock_location sl on sl.id = sm.location_dest_id
                          where sl.usage <> 'customer'),
     location_info_duong as (select ola.order_line_id, sl.id as location_id
                             from order_line_duong ola
                                      left join stock_picking sp
                                                on sp.pos_order_id = ola.order_id
                                      left join stock_move sm on sm.picking_id = sp.id and sm.product_id = ola.product_id
                                      left join stock_location sl on sl.id = sm.location_id
                             where sl.usage <> 'customer'),
     location_finals as (select *
                         from location_info_am
                         union all
                         select *
                         from location_info_duong),
     data_finals as ("""

        query += f"""
                     select wh.name                                                                                                   as kho,
                            sl.complete_name                                                                                          as dia_diem,
                            pp.barcode                                                                                                as ma_sp,
                            pt.name ->> 'vi_VN'                                                                                       as ten_sp,
                            uom.name ->> 'vi_VN'                                                                                      as don_vi,
                            greatest(pol.qty, 0)                                                                                      as sl_ban,
                            least(pol.qty, 0)                                                                                         as sl_tra,
                            pol.qty                                                                                                   as sl,
                            {'pol.original_price' if self.is_with_tax else '(pol.original_price / (1 + coalesce(olf.tax_percent, 0) / 100))::int'} as don_gia,
                            coalesce(olf.tax_percent, 0)                                                                              as thue_suat,
                            (pol.qty * pol.original_price * (coalesce(olf.tax_percent, 0) / 100) / (1 + coalesce(olf.tax_percent, 0) / 100))
                                - (coalesce(dd.khuyen_mai_bh, 0) / (1 + coalesce(olf.tax_percent, 0) / 100))                          as thue_gtgt,
                            case
                                when pol.qty < 0 then pol.price_subtotal
                                else (pol.price_subtotal -
                                      (coalesce(dd.giam_tru_dt, 0) /
                                       (1 + coalesce(olf.tax_percent, 0) / 100)))::int
                                end                                                                                                   as doanh_thu_bh,
                            {'coalesce(dd.giam_tru_dt, 0)' if self.is_with_tax else '(coalesce(dd.giam_tru_dt, 0) / (1 + coalesce(olf.tax_percent, 0) / 100))::int'} as giam_tru_dt,
                            {'coalesce(dd.khuyen_mai_bh, 0)' if self.is_with_tax else '(coalesce(dd.khuyen_mai_bh, 0) / (1 + coalesce(olf.tax_percent, 0) / 100))::int'} as khuyen_mai_bh,
                            coalesce(ttt.tong_tt, 0)                                                                                  as tong_tt,
                            'Cửa hàng'                                                                                                as kenh_ban,
                            po.date_order,
                            to_char(coalesce(org_po.date_order, po.date_order) + interval '{tz_offset} h', 'MM/YYYY')                           as thoi_gian,
                            case
                                when pol.is_reward_line = true
                                    and pol.with_purchase_condition = true then 3
                                when pol.is_reward_line = true
                                    and pol.with_purchase_condition = any (array [false, null]) then 2
                                else 1 end                                                                                            as loai_hang,
                            to_date(to_char(coalesce(org_po.date_order, po.date_order) + interval '{tz_offset} h', 'YYYY-MM-01'), 'YYYY-MM-DD') as thang
                     from pos_order_line pol
                              join pos_order po on po.id = pol.order_id
                              join order_line_finals olf on olf.order_line_id = pol.id
                              left join pos_order org_po on org_po.id = olf.origin_order_id
                              left join location_finals lf on lf.order_line_id = pol.id
                              left join stock_location sl on lf.location_id = sl.id
                              left join stock_warehouse wh on wh.id = sl.warehouse_id
                              left join discount_datas dd on dd.order_line_id = pol.id
                              left join tong_thanh_toan ttt on ttt.order_line_id = pol.id
                              join product_product pp on pp.id = pol.product_id
                              join product_template pt on pt.id = pp.product_tmpl_id
                              join uom_uom uom on uom.id = pt.uom_id)
select row_number() over (order by thang desc, loai_hang, thue_suat) as stt,
       kho,
       dia_diem,
       ma_sp,
       ten_sp,
       don_vi,
       sum(sl_ban)::int                                         as sl_ban,
       sum(sl_tra)::int                                         as sl_tra,
       sum(sl)::int                                             as sl,
       {'don_gia,' if self.is_get_price_unit else ''}
       thue_suat,
       sum(thue_gtgt)::int                                      as thue_gtgt,
       sum(doanh_thu_bh)::int                                   as doanh_thu_bh,
       sum(giam_tru_dt)::int                                    as giam_tru_dt,
       sum(khuyen_mai_bh)::int                                  as khuyen_mai_bh,
       sum(tong_tt)::int                                        as tong_tt,
       kenh_ban,
       loai_hang,
       thoi_gian,
       thang
from data_finals
group by kho, dia_diem, ma_sp, ten_sp, don_vi, {'don_gia,' if self.is_get_price_unit else ''} thue_suat, kenh_ban, loai_hang, thoi_gian, thang
order by stt
"""
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        if not any([self.is_pos_order, self.is_wholesale, self.is_ecommerce, self.is_inter_company]):
            raise ValidationError('Vui lòng chọn kênh bán')
        if not self.warehouse_ids:
            raise ValidationError('Vui lòng chọn kho')
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        titles = copy.copy(TITLES)
        if not self.is_get_price_unit:
            titles.pop(9)
        values.update({
            'titles': titles,
            "data": data,
            'column_add': self.is_get_price_unit,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tích - tiêu điểm theo cửa hàng')
        sheet.set_row(3, 25)
        sheet.set_row(6, 35)
        sheet.freeze_panes(7, 0)
        company = self.env['res.company'].search([('id', 'in', allowed_company)])
        cong_ty = ', '.join(company.filtered(lambda f: f.name).mapped('name'))
        dia_chi = ', '.join(company.filtered(lambda f: f.street).mapped('street'))
        sheet.write(0, 0, f'Công ty: {cong_ty}', formats.get('normal_format'))
        sheet.write(1, 0, f'Địa chỉ: {dia_chi}', formats.get('normal_format'))
        sheet.merge_range(3, 0, 3, len(data.get('titles')) - 1, 'BẢNG KÊ HÀNG HÓA XUẤT HÓA ĐƠN', formats.get('header_format'))
        sheet.merge_range(4, 0, 4, len(data.get('titles')) - 1, f'Báo cáo tháng: {"%.2d/%.4d" % (int(self.month.code), self.year)}', formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(6, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(data.get('titles')) - 1, 20)
        row = 7
        loai = 0
        thang_x = ''
        column_x = 10 if self.is_get_price_unit else 9
        for value in data.get('data'):
            thoi_gian = value.get('thoi_gian')
            loai_hang = value.get('loai_hang')
            if thang_x != thoi_gian:
                sheet.merge_range(row, 0, row, len(data.get('titles')) - 1, thoi_gian, formats.get('month_format'))
                loai = 0
                thang_x = thoi_gian
                row += 1
            elif loai != loai_hang:
                if loai_hang == 2:
                    sheet.merge_range(row, 0, row, len(data.get('titles')) - 1, 'Hàng tặng có điều kiện', formats.get('subtotal_format'))
                    row += 1
                elif loai_hang == 3:
                    sheet.merge_range(row, 0, row, len(data.get('titles')) - 1, 'Hàng tặng không điều kiện', formats.get('subtotal_format'))
                    row += 1
                loai = loai_hang
            sheet.write(row, 0, value.get('stt'), formats.get('center_format'))
            sheet.write(row, 1, value.get('kho') or '', formats.get('normal_format'))
            sheet.write(row, 2, value.get('dia_diem') or '', formats.get('normal_format'))
            sheet.write(row, 3, value.get('ma_sp') or '', formats.get('normal_format'))
            sheet.write(row, 4, value.get('ten_sp') or '', formats.get('normal_format'))
            sheet.write(row, 5, value.get('don_vi') or '', formats.get('normal_format'))
            sheet.write(row, 6, value.get('sl_ban') or 0, formats.get('int_number_format'))
            sheet.write(row, 7, value.get('sl_tra') or 0, formats.get('int_number_format'))
            sheet.write(row, 8, value.get('sl') or 0, formats.get('int_number_format'))
            if self.is_get_price_unit:
                sheet.write(row, 9, value.get('don_gia') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x, f"{value.get('thue_suat') or 0}%", formats.get('normal_format'))
            sheet.write(row, column_x + 1, value.get('thue_gtgt') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x + 2, value.get('doanh_thu_bh') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x + 3, value.get('giam_tru_dt') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x + 4, value.get('khuyen_mai_bh') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x + 5, value.get('tong_tt') or 0, formats.get('int_number_format'))
            sheet.write(row, column_x + 6, value.get('kenh_ban') or '', formats.get('normal_format'))
            row += 1

    def print_xlsx(self):
        if not any([self.is_pos_order, self.is_wholesale, self.is_ecommerce, self.is_inter_company]):
            raise ValidationError('Vui lòng chọn kênh bán')
        if not self.warehouse_ids:
            raise ValidationError('Vui lòng chọn kho')
        return super().print_xlsx()

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        month_format = {
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#98cfe1',
            'color': 'f54242',
        }
        month_format = workbook.add_format(month_format)
        res.update({
            'month_format': month_format,
        })
        res.get('header_format').set_align('center')
        res.get('italic_format').set_align('center')
        return res
