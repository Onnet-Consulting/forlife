# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ForlifeHrPayrollXlsx(models.AbstractModel):
    _name = "report.forlife_hr_payroll.salary_record_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Salary Record Report"

    def generate_xlsx_report(self, workbook, data, salary_record):
        if not salary_record:
            raise ValidationError(_('Salary Record not found.'))
        salary_record = salary_record[0] if salary_record else False
        sh_header = workbook.add_worksheet("Header")
        sh_luong = workbook.add_worksheet("Lương")
        sh_ttn = workbook.add_worksheet("Tổng thu nhập")
        sh_bh = workbook.add_worksheet("BH+phí CĐ+thuế TNCN cần chi trả")
        sh_tt = workbook.add_worksheet("Truy thu NLĐ")
        sh_ltd = workbook.add_worksheet("Lương tồn đọng")
        _format = workbook.add_format({
            'bold': True,
            'bg_color': '#a8cde3',
            'text_wrap': True,
            'valign': 'vcenter',
        })
        self.write_sheet_header(sh_header, salary_record, _format)
        self.write_sheet_luong(sh_luong, salary_record.salary_record_main_ids, _format)
        self.write_sheet_ttn(sh_ttn, salary_record.salary_total_income_ids, _format)
        self.write_sheet_bh(sh_bh, salary_record.salary_supplementary_ids, _format)
        self.write_sheet_tt(sh_tt, salary_record.salary_arrears_ids, _format)
        self.write_sheet_ltd(sh_ltd, salary_record.salary_backlog_ids, _format)

    def write_sheet_header(self, sh_header, salary_record, _format):
        header = ['Công ty', 'Loại', 'Năm', 'Tháng', 'Mô tả']
        for i, name in enumerate(header):
            sh_header.write(0, i, name, _format)
        sh_header.set_row(0, 25)
        sh_header.set_column(0, len(header) - 1, 20)
        sh_header.write(1, 0, salary_record.company_id.name)
        sh_header.write(1, 1, salary_record.type_id.name)
        sh_header.write(1, 2, salary_record.year)
        sh_header.write(1, 3, salary_record.month)
        sh_header.write(1, 4, salary_record.note or '')

    def write_sheet_luong(self, sh_luong, salary_record_main, _format):
        header = ['Mục đích tính lương', 'Mã phòng/bp', 'Tên phòng/bộ phận', 'Mã cost center', 'Mã Dự án', 'Tổng thu nhập', 'Ký quỹ', 'TKDP', 'Phạt vi phạm', 'Trừ TTHH', 'Trừ hàng lỗi',
                  'Trừ chi phí đồng phục FM', 'Phạt doanh số', 'Truy thu lương', 'Truy thu phụ cấp', 'Tạm ứng', 'Truy thu BH vào lương', 'Trừ khác', 'Mức BHXH', 'BHXH+BHBNN-TNLĐ Công ty chi trả',
                  'BHYT Công ty chi trả', 'BHTN Công ty chi trả', 'TỔNG CHI PHÍ BH Công ty chi trả', 'BHXH NLĐ chi trả', 'BHYT NLĐ chi trả', 'BHTN NLĐ chi trả',
                  'TỔNG CHI PHÍ BH NLĐ chi trả', 'Công đoàn phí công ty nộp', 'Công đoàn phí NLĐ nộp', 'Thuế TNCN NLĐ nộp', 'Tổng trừ', 'Thực lĩnh', 'Số lượng nhân sự']
        for i, name in enumerate(header):
            sh_luong.write(0, i, name, _format)
        sh_luong.set_row(0, 40)
        sh_luong.set_column(0, len(header) - 1, 20)
        for row, value in enumerate(salary_record_main, start=1):
            sh_luong.write(row, 0, value.purpose_id.display_name)
            sh_luong.write(row, 1, value.department_id.code)
            sh_luong.write(row, 2, value.department_id.name)
            sh_luong.write(row, 3, value.analytic_account_id.code)
            sh_luong.write(row, 4, value.project_code or '')
            sh_luong.write(row, 5, value.x_ttn or 0)
            sh_luong.write(row, 6, value.x_kq or 0)
            sh_luong.write(row, 7, value.x_tkdp or 0)
            sh_luong.write(row, 8, value.x_pvp or 0)
            sh_luong.write(row, 9, value.x_tthh or 0)
            sh_luong.write(row, 10, value.x_thl or 0)
            sh_luong.write(row, 11, value.x_dpfm or 0)
            sh_luong.write(row, 12, value.x_pds or 0)
            sh_luong.write(row, 13, value.x_ttl or 0)
            sh_luong.write(row, 14, value.x_ttpc or 0)
            sh_luong.write(row, 15, value.x_tu or 0)
            sh_luong.write(row, 16, value.x_ttbh or 0)
            sh_luong.write(row, 17, value.x_tk or 0)
            sh_luong.write(row, 18, value.x_bhxh_level or 0)
            sh_luong.write(row, 19, value.x_bhxh_bhbnn_tnld_ct or 0)
            sh_luong.write(row, 20, value.x_bhyt_ct or 0)
            sh_luong.write(row, 21, value.x_bhtn_ct or 0)
            sh_luong.write(row, 22, value.x_tbh_ct or 0)
            sh_luong.write(row, 23, value.x_bhxh_nld or 0)
            sh_luong.write(row, 24, value.x_bhyt_nld or 0)
            sh_luong.write(row, 25, value.x_bhtn_nld or 0)
            sh_luong.write(row, 26, value.x_tbh_nld or 0)
            sh_luong.write(row, 27, value.x_cdp_ct or 0)
            sh_luong.write(row, 28, value.x_cdp_nld or 0)
            sh_luong.write(row, 29, value.x_tncn or 0)
            sh_luong.write(row, 30, value.x_tt or 0)
            sh_luong.write(row, 31, value.x_tl or 0)
            sh_luong.write(row, 32, value.x_slns or 0)

    def write_sheet_ttn(self, sh_ttn, salary_total_income, _format):
        header = [' Mục đích tính lương', 'Mã phòng/bp', 'Tên phòng/bộ phận', 'Mã cost center', 'Mã Dự án', 'Mã lệnh sản xuất', 'Mã vụ việc', 'Tổng thu nhập', 'Ghi chú']
        for i, name in enumerate(header):
            sh_ttn.write(0, i, name, _format)
        sh_ttn.set_row(0, 40)
        sh_ttn.set_column(0, len(header) - 1, 20)
        for row, value in enumerate(salary_total_income, start=1):
            sh_ttn.write(row, 0, value.purpose_id.display_name)
            sh_ttn.write(row, 1, value.department_id.code)
            sh_ttn.write(row, 2, value.department_id.name)
            sh_ttn.write(row, 3, value.analytic_account_id.code)
            sh_ttn.write(row, 4, value.project_code or '')
            sh_ttn.write(row, 5, value.manufacture_order_code or '')
            sh_ttn.write(row, 6, value.internal_order_code or '')
            sh_ttn.write(row, 7, value.x_ttn or 0)
            sh_ttn.write(row, 8, value.note or '')

    def write_sheet_bh(self, sh_bh, salary_supplementary, _format):
        header = ['Mục đích tính lương', 'Mã phòng/bp', 'Tên phòng/bộ phận', 'Mã cost center', 'Mã dự án', 'Mã lệnh sản xuất', 'Mã vụ việc', 'Mức BHXH',
                  'BHXH NLĐ chi trả', 'BHYT NLĐ chi trả', 'BHTN NLĐ chi trả', 'TỔNG CHI PHÍ BH NLĐ chi trả', 'BHXH+BHBNN-TNLĐ Công ty chi trả', 'BHYT Công ty chi trả',
                  'BHTN Công ty chi trả', 'TỔNG CHI PHÍ BH Công ty chi trả', 'Công đoàn phí công ty nộp', 'Công đoàn phí NLĐ nộp', 'Thuế TNCN NLĐ nộp', 'Ghi chú']
        for i, name in enumerate(header):
            sh_bh.write(0, i, name, _format)
        sh_bh.set_row(0, 40)
        sh_bh.set_column(0, len(header) - 1, 20)
        for row, value in enumerate(salary_supplementary, start=1):
            sh_bh.write(row, 0, value.purpose_id.display_name)
            sh_bh.write(row, 1, value.department_id.code)
            sh_bh.write(row, 2, value.department_id.name)
            sh_bh.write(row, 3, value.analytic_account_id.code)
            sh_bh.write(row, 4, value.project_code or '')
            sh_bh.write(row, 5, value.manufacture_order_code or '')
            sh_bh.write(row, 6, value.internal_order_code or '')
            sh_bh.write(row, 7, value.x_bhxh_level or 0)
            sh_bh.write(row, 8, value.x_bhxh_nld or 0)
            sh_bh.write(row, 9, value.x_bhyt_nld or 0)
            sh_bh.write(row, 10, value.x_bhtn_nld or 0)
            sh_bh.write(row, 11, value.x_tbh_nld or 0)
            sh_bh.write(row, 12, value.x_bhxh_bhbnn_tnld_ct or 0)
            sh_bh.write(row, 13, value.x_bhyt_ct or 0)
            sh_bh.write(row, 14, value.x_bhtn_ct or 0)
            sh_bh.write(row, 15, value.x_tbh_ct or 0)
            sh_bh.write(row, 16, value.x_cdp_ct or 0)
            sh_bh.write(row, 17, value.x_cdp_nld or 0)
            sh_bh.write(row, 18, value.x_tncn or 0)
            sh_bh.write(row, 19, value.note or '')

    def write_sheet_tt(self, sh_tt, salary_arrears, _format):
        header = ['Mục đích tính lương', 'Mã NV', 'Họ tên', 'Mã phòng/bp', 'Tên phòng/bộ phận', 'Mã cost center', 'Mã Dự án', 'Mã lệnh sản xuất', 'Mã vụ việc',
                  'Ký quỹ', 'TKDP', 'Phạt vi phạm', 'Trừ TTHH', 'Trừ hàng lỗi', 'Trừ đồng phục', 'Phạt doanh số', 'Truy thu lương', 'Truy thu phụ cấp',
                  'Tạm ứng', 'Trừ khác', 'Công nợ BHXH NLĐ chi trả', 'Công nợ BHYT NLĐ chi trả', 'Công nợ BHTN NLĐ chi trả', 'Truy thu BH vào lương', 'Ghi chú ']
        for i, name in enumerate(header):
            sh_tt.write(0, i, name, _format)
        sh_tt.set_row(0, 40)
        sh_tt.set_column(0, len(header) - 1, 20)
        for row, value in enumerate(salary_arrears, start=1):
            sh_tt.write(row, 0, value.purpose_id.display_name)
            sh_tt.write(row, 1, value.employee_id.code)
            sh_tt.write(row, 2, value.employee_id.name)
            sh_tt.write(row, 3, value.department_id.code)
            sh_tt.write(row, 4, value.department_id.name)
            sh_tt.write(row, 5, value.analytic_account_id.code)
            sh_tt.write(row, 6, value.project_code or '')
            sh_tt.write(row, 7, value.manufacture_order_code or '')
            sh_tt.write(row, 8, value.internal_order_code or '')
            sh_tt.write(row, 9, value.x_kq or 0)
            sh_tt.write(row, 10, value.x_tkdp or 0)
            sh_tt.write(row, 11, value.x_pvp or 0)
            sh_tt.write(row, 12, value.x_tthh or 0)
            sh_tt.write(row, 13, value.x_thl or 0)
            sh_tt.write(row, 14, value.x_dpfm or 0)
            sh_tt.write(row, 15, value.x_pds or 0)
            sh_tt.write(row, 16, value.x_ttl or 0)
            sh_tt.write(row, 17, value.x_ttpc or 0)
            sh_tt.write(row, 18, value.x_tu or 0)
            sh_tt.write(row, 19, value.x_tk or 0)
            sh_tt.write(row, 20, value.x_bhxh_cn or 0)
            sh_tt.write(row, 21, value.x_bhyt_cn or 0)
            sh_tt.write(row, 22, value.x_bhxh_bhbnn_tnld_cn or 0)
            sh_tt.write(row, 23, value.x_ttbh or 0)
            sh_tt.write(row, 24, value.note or '')

    def write_sheet_ltd(self, sh_ltd, salary_backlog, _format):
        header = ['STT', 'Mã NV', 'Họ tên', 'Mã phòng/bộ phận', 'Tên phòng/bộ phận', 'Số tiền', 'Tháng']
        for i, name in enumerate(header):
            sh_ltd.write(0, i, name, _format)
        sh_ltd.set_row(0, 25)
        sh_ltd.set_column(0, len(header) - 1, 20)
        for row, value in enumerate(salary_backlog, start=1):
            sh_ltd.write(row, 0, row)
            sh_ltd.write(row, 1, value.employee_id.code)
            sh_ltd.write(row, 2, value.employee_id.name)
            sh_ltd.write(row, 3, value.department_id.code)
            sh_ltd.write(row, 4, value.department_id.name)
            sh_ltd.write(row, 5, value.amount or 0)
            sh_ltd.write(row, 6, value.period or '')
