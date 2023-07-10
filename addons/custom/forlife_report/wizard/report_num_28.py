# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

TITLES = [
    'Số PO', 'Ngày tạo PO', 'Ngày nhận hàng dự kiến', 'Ghi chú',
    'Kho', 'Số phiếu kho', 'STT dòng', 'Barcode (*)', 'Tên SP',
    'Màu', 'Size', 'Số lượng đặt hàng', 'Đơn vị tính (*)', 'Số lượng xác nhận',
    'Phần dở dang của',
]


class ReportNum28(models.TransientModel):
    _name = 'report.num28'
    _inherit = 'report.base'
    _description = 'Báo cáo danh sách phiếu nhập kho mua hàng'

    request_id = fields.Many2many('purchase.order', string='Số PO',
                                  domain=[('custom_state', 'not in', ('cancel', 'close'))])
    location_id = fields.Many2one('stock.location', string='Kho')
    status = fields.Selection([('to invoice', 'Chưa hoàn thành'), ('invoiced', 'Đã hoàn thành')], string='Trạng thái')

    def _get_query(self):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        query = f"""
            select 
                po.name as ten,
                TO_CHAR(
                    po.date_order,
                    'dd/mm/yyyy'
                ) as ngay_tao_po,
                TO_CHAR(
                    po.receive_date,
                    'dd/mm/yyyy'
                ) as ngay_du_kien,
                po.note as ghi_chu,
                sl.name as kho,
                sl.name as so_phieu_kho,
                row_number () over (partition by sm.id order by sm.create_date) num,
                pp.barcode as barcode,
                COALESCE(pt.name->>'vi_VN', pt.name->>'en_US') as ten_sp,
                attr.attrs->>'{attr_value.get('mau_sac', '')}' as mau,
                attr.attrs->>'{attr_value.get('size', '')}' as size,
                sm.product_uom_qty as sl_nhu_cau,
                COALESCE(uu.name->>'vi_VN', uu.name->>'en_US') as dvt,
                '' as sl_nhan,
                sp2.name as phan_do_dang
                
            from purchase_order po 
            join purchase_order_line pol on po.id = pol.order_id 
            join stock_move sm on pol .id = sm.purchase_line_id 
            join uom_uom uu on sm.product_uom = uu.id
            join stock_picking sp on sp.id = sm.picking_id
            join stock_location sl on sm.location_dest_id = sl.id
            left join stock_picking sp2 on sp2.id = sp.backorder_id
            join product_product pp on sm.product_id = pp.id 
            join product_template pt on pp.product_tmpl_id = pt.id 
            left join (
                select
                    product_id,
                    json_object_agg(attrs_code, value) as attrs
                from (
                    select
                        pp.id as product_id,
                        pa.attrs_code as attrs_code,
                        array_agg(coalesce(pav.name::json -> 'vi_VN', pav.name::json -> 'en_US')) as value
                    from
                        product_template_attribute_line ptal
                    left join product_product pp on pp.product_tmpl_id = ptal.product_tmpl_id
                    left join product_attribute_value_product_template_attribute_line_rel rel on rel.product_template_attribute_line_id = ptal.id
                    left join product_attribute pa on ptal.attribute_id = pa.id
                    left join product_attribute_value pav on pav.id = rel.product_attribute_value_id
                    where
                        pa.attrs_code is not null
                    group by
                        pp.id,
                        pa.attrs_code
                ) as att
                group by product_id
            ) attr on attr.product_id = pp.id
            
            where 1 = 1 and po.is_return is null

        """

        if self.request_id:
            query += f""" and po.id = any(array{self.request_id.ids})"""
        if self.location_id:
            query += f""" and sp.location_dest_id = {self.location_id.id}"""
        if self.status:
            query += f""" and po.invoice_status_fake = '{self.status}'"""
        query += " ORDER BY sp.name, num;"
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
        sheet = workbook.add_worksheet('Báo cáo danh sách phiếu nhập kho mua hàng')
        sheet.set_row(0, 25)
        sheet.write(0, 0, 'Báo cáo danh sách phiếu nhập kho mua hàng', formats.get('header_format'))
        sheet.write(2, 0, 'Số PO: %s' % self.request_id.mapped('name') or '', formats.get('italic_format'))
        sheet.write(2, 2, 'Kho: %s' % (self.location_id.name or ''), formats.get('italic_format'))
        sheet.write(2, 4, 'Trạng thái: %s' % (dict(self._fields['status'].selection).get(self.status)),
                    formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(4, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES), 20)
        row = 5
        for value in data.get('data'):
            sheet.write(row, 0, value.get('ten'), formats.get('center_format'))
            sheet.write(row, 1, value.get('ngay_tao_po'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('ngay_du_kien'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('ghi_chu'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('kho'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('so_phieu_kho'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('num'), formats.get('int_number_format'))
            sheet.write(row, 7, value.get('barcode'), formats.get('normal_format'))
            sheet.write(row, 8, value.get('ten_sp'), formats.get('normal_format'))
            sheet.write(row, 9, value.get('mau'), formats.get('int_number_format'))
            sheet.write(row, 10, value.get('size'), formats.get('int_number_format'))
            sheet.write(row, 11, value.get('sl_nhu_cau'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('dvt'), formats.get('int_number_format'))
            sheet.write(row, 13, value.get('sl_nhan'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('phan_do_dang'), formats.get('int_number_format'))
            row += 1
