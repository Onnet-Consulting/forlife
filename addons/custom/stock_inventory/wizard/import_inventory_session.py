# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64
import copy


class ImportInventorySessionWizard(models.TransientModel):
    _name = 'import.inventory.session.wizard'
    _inherit = 'report.base'
    _description = 'Dữ liệu kiểm đếm'

    import_file = fields.Binary(attachment=False, string='Tải lên tệp')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Tệp lỗi')
    error_file_name = fields.Char(default='Error.txt')
    inv_id = fields.Many2one('stock.inventory', 'Phiếu kiểm kê')

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('CLKK')
        sheet.freeze_panes(0, 10)
        sheet.set_row(0, 30)
        sheet.set_row(5, 30)
        sheet.set_row(6, 35)
        sheet.set_row(7, 32)
        sheet.write(0, 0, f'CHÊNH LỆCH KIỂM KÊ CỬA HÀNG {self.inv_id.warehouse_id.name or ""}', formats.get('header_format'))
        sheet.write(1, 0, '', formats.get('format_color1'))
        sheet.write(2, 0, '', formats.get('format_color2'))
        sheet.write(3, 0, '', formats.get('format_color3'))
        sheet.write(4, 0, '', formats.get('format_color4'))
        sheet.write(1, 1, '<= Dữ liệu')
        sheet.write(2, 1, '<= Hàng kiểm đếm được tính vào số lượng kiểm kê')
        sheet.write(3, 1, '<= Hàng bị trừ khỏi số liệu kiểm kê')
        sheet.write(4, 1, '<= Kết quả')
        sheet.merge_range('A6:B6', f'LẤY TỒN NGÀY: {self.inv_id.date.strftime("%d/%m/%Y") if self.inv_id.date else ""}', formats.get('normal_format'))
        sheet.merge_range('P6:Q6', 'HÀNG LỖI', formats.get('format_color5'))
        sheet.merge_range('R6:S6', 'XỬ LÝ HÀNG TÌM ĐƯỢC NGAY TẠI CỬA HÀNG', formats.get('format_color5'))
        sheet.merge_range('T6:U6', 'XỬ LÝ HÓA ĐƠN VÀ NTL', formats.get('format_color5'))
        sheet.merge_range('V6:W6', 'XỬ LÝ PHẦN SAI XÓT', formats.get('format_color5'))
        sheet.merge_range('Y6:Z6', 'CÂN ĐỐI SAU XÁC NHẬN LẦN 1', formats.get('format_color5'))
        TITLES = [
            'STT', 'MÃ HÀNG', 'TÊN HÀNG', 'MÀU', 'SIZE', 'NHÓM SẢN PHẨM', 'ĐƠN VỊ', 'GIÁ', 'TỒN PHẦN MỀM',
            'KIỂM KÊ THỰC TẾ', 'PHIÊN ĐẾM BỔ SUNG', 'HÀNG KHÔNG ĐẾM KIỂM', 'TÚI BÁN HÀNG', 'HÀNG KHÔNG TEM',
            'HÀNG KHÔNG CHEAT ĐƯỢC MÃ VẠCH', 'HÀNG LỖI CHƯA ĐƯỢC DUYỆT', 'HÀNG LỖI ĐÃ ĐƯỢC DUYỆT', 'THÊM LẦN 1', 'BỚT LẦN 1',
            'CỘNG HÀNG BÁN / NTL CHƯA KIỂM', 'TRỪ HÀNG BÁN ĐÃ KIỂM', 'BỔ XUNG HÀNG CHƯA ĐƯỢC CHEAT', 'TRỪ HÀNG KIỂM ĐÚP',
            'TỔNG KIỂM KÊ THỰC TẾ LẦN 1', 'THÊM LẦN 2', 'BỚT LẦN 2', 'TỔNG KIỂM KÊ THỰC TẾ', 'CHÊNH LỆCH KIỂM KÊ', 'NOTE', 'PHIÊN ĐẾM']
        for idx, title in enumerate(TITLES):
            sheet.write(6, idx, title, formats.get('title_format'))
        NOTES = [
            '(1)', '(2)', '(3)', '(4)', '(5)', '(6)', '(7)', '(8)', '(9)', '(10)', '(11)', '(12)', '(13)', '(14)', '(15)',
            '(16)=(2)+(3)+(4)+(5)+(6)+(7)+(8)+(9)+(10)-(11)+(12)-(13)+(14)-(15)', '(17)', '(18)', '(19)=(16)+(17)-(18)', '(20)=(1)-(19)'
        ]
        sheet.set_column(1, len(TITLES) - 1, 15)
        for idx, title in enumerate(NOTES):
            if idx == 0:
                sheet.write(7, idx + 8, title, formats.get('format_color1'))
            elif idx in (10, 12, 14, 17):
                sheet.write(7, idx + 8, title, formats.get('format_color3'))
            elif idx in (15, 18, 19):
                sheet.write(7, idx + 8, title, formats.get('format_color4'))
            else:
                sheet.write(7, idx + 8, title, formats.get('format_color2'))
        row = 8
        stt = 1
        for line in self.inv_id.detail_ids:
            sheet.write(row, 0, stt, formats.get('center_format'))
            sheet.write(row, 1, line.ma_hang or '', formats.get('normal_format'))
            sheet.write(row, 2, line.ten_hang or '', formats.get('normal_format'))
            sheet.write(row, 3, line.mau or '', formats.get('normal_format'))
            sheet.write(row, 4, line.size or '', formats.get('normal_format'))
            sheet.write(row, 5, line.nhom_san_pham or '', formats.get('normal_format'))
            sheet.write(row, 6, line.don_vi or '', formats.get('normal_format'))
            sheet.write(row, 7, line.gia or 0, formats.get('int_number_format'))
            sheet.write(row, 8, line.ton_phan_mam, formats.get('int_number_format'))
            sheet.write(row, 9, line.kiem_ke_thuc_te, formats.get('int_number_format'))
            sheet.write(row, 10, line.phien_dem_bo_sung, formats.get('int_number_format'))
            sheet.write(row, 11, line.hang_khong_kiem_dem, formats.get('int_number_format'))
            sheet.write(row, 12, line.tui_ban_hang, formats.get('int_number_format'))
            sheet.write(row, 13, line.hang_khong_tem, formats.get('int_number_format'))
            sheet.write(row, 14, line.hang_khong_cheat_duoc, formats.get('int_number_format'))
            sheet.write(row, 15, line.hang_loi_chua_duyet, formats.get('int_number_format'))
            sheet.write(row, 16, line.hang_loi_da_duyet, formats.get('int_number_format'))
            sheet.write(row, 17, line.them1, formats.get('int_number_format'))
            sheet.write(row, 18, line.bot1, formats.get('int_number_format'))
            sheet.write(row, 19, line.cong_hang_ban_ntl_chua_kiem, formats.get('int_number_format'))
            sheet.write(row, 20, line.tru_hang_ban_da_kiem, formats.get('int_number_format'))
            sheet.write(row, 21, line.bo_sung_hang_chua_cheat, formats.get('int_number_format'))
            sheet.write(row, 22, line.tru_hang_kiem_dup, formats.get('int_number_format'))
            sheet.write(row, 23, line.tong_kiem_ke_thuc_te_1, formats.get('int_number_format'))
            sheet.write(row, 24, line.them2, formats.get('int_number_format'))
            sheet.write(row, 25, line.bot2, formats.get('int_number_format'))
            sheet.write(row, 26, line.tong_kiem_dem_thuc_te, formats.get('int_number_format'))
            sheet.write(row, 27, line.chenh_lech_kiem_ke, formats.get('int_number_format'))
            sheet.write(row, 28, line.ghi_chu or '', formats.get('normal_format'))
            sheet.write(row, 29, line.phien_dem or '', formats.get('normal_format'))
            row += 1
            stt += 1

    def download_template_file(self):
        attachment_id = self.env.ref(f'stock_inventory.{self._context.get("template_xml_id")}')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    def get_filename(self):
        return f"CLKK {self.inv_id.warehouse_id.name or ''} {self.inv_id.date.strftime('%d%m%Y')}"

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút import !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        values = list(self.env['res.utility'].read_xls_book(workbook, 0))[self._context.get('start_row') or 1:]
        return getattr(self, self._context.get('template_xml_id').replace('template', ''), None)(values)

    def _import_inventory_session_add(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            phien_dem_bo_sung = float(val[1] or 0)
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'phien_dem_bo_sung': phien_dem_bo_sung
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals, 'web') if vals else False

    def _import_inventory_session_add2(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            them2 = float(val[1] or 0)
            bot2 = float(val[2] or 0)
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'them2': them2,
                    'bot2': bot2,
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals, 'add') if vals else False

    def _import_inventory_session_other(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            hang_khong_kiem_dem = float(val[1] or 0)
            tui_ban_hang = float(val[2] or 0)
            hang_khong_tem = float(val[3] or 0)
            hang_khong_cheat_duoc = float(val[4] or 0)
            hang_loi_chua_duyet = float(val[5] or 0)
            hang_loi_da_duyet = float(val[6] or 0)
            them1 = float(val[7] or 0)
            bot1 = float(val[8] or 0)
            cong_hang_ban_ntl_chua_kiem = float(val[9] or 0)
            tru_hang_ban_da_kiem = float(val[10] or 0)
            bo_sung_hang_chua_cheat = float(val[11] or 0)
            tru_hang_kiem_dup = float(val[12] or 0)
            ghi_chu = val[13]
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'hang_khong_kiem_dem': hang_khong_kiem_dem,
                    'tui_ban_hang': tui_ban_hang,
                    'hang_khong_tem': hang_khong_tem,
                    'hang_khong_cheat_duoc': hang_khong_cheat_duoc,
                    'hang_loi_chua_duyet': hang_loi_chua_duyet,
                    'hang_loi_da_duyet': hang_loi_da_duyet,
                    'them1': them1,
                    'bot1': bot1,
                    'cong_hang_ban_ntl_chua_kiem': cong_hang_ban_ntl_chua_kiem,
                    'tru_hang_ban_da_kiem': tru_hang_ban_da_kiem,
                    'bo_sung_hang_chua_cheat': bo_sung_hang_chua_cheat,
                    'tru_hang_kiem_dup': tru_hang_kiem_dup,
                    'ghi_chu': ghi_chu,
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals, 'other') if vals else False

    def _action_import(self, vals, type):
        if type in ('other', 'add'):
            old_session = self.env['inventory.session'].search([('inv_id', '=', self.inv_id.id), ('type', '=', type)])
            if old_session:
                old_session.with_context(not_update_inv=True).sudo().action_inactive_session()
        res = self.env['inventory.session'].sudo().create({
            'inv_id': self.inv_id.id,
            'type': type,
            'line_ids': vals,
        })
        action = self.env.ref('stock_inventory.inventory_session_form_view_action').read()[0]
        action['res_id'] = res.id
        return action

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('stock_inventory.import_inventory_session_action').read()[0]
        action['res_id'] = self.id
        return action

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        normal_format = {
            'align': 'center',
            'valign': 'vcenter',
            'border': True,
            'text_wrap': True,
        }
        format_color1 = copy.copy(normal_format)
        format_color1.update({'bg_color': '#9acbf5'})

        format_color2 = copy.copy(normal_format)
        format_color2.update({'bg_color': '#5c915c'})

        format_color3 = copy.copy(normal_format)
        format_color3.update({'bg_color': '#f7d894'})

        format_color4 = copy.copy(normal_format)
        format_color4.update({'bg_color': '#eba652'})

        format_color5 = copy.copy(normal_format)
        format_color5.update({'bg_color': '#a2dbfa'})

        format_color1 = workbook.add_format(format_color1)
        format_color2 = workbook.add_format(format_color2)
        format_color3 = workbook.add_format(format_color3)
        format_color4 = workbook.add_format(format_color4)
        format_color5 = workbook.add_format(format_color5)
        res.update({
            'format_color1': format_color1,
            'format_color2': format_color2,
            'format_color3': format_color3,
            'format_color4': format_color4,
            'format_color5': format_color5,
        })
        return res
