# -*- coding:utf-8 -*-

AVAILABLE_REPORT = {
    'report.num2': {
        'module': 'Kho',
        'name': 'Tồn kho theo giá bán',
        'reportTemplate': 'ReportNum2Template',
        'reportPager': True,
        'tag': 'report_num2_action',
    },
    'report.num3': {
        'module': 'Kho',
        'name': 'Tồn kho theo chi nhánh/khu vực',
        'reportTemplate': 'ReportNum3Template',
        'reportPager': True,
        'tag': 'report_num3_action',
    },
    'report.num4': {
        'module': 'Kho',
        'name': 'Tồn kho theo sản phẩm',
        'reportTemplate': 'ReportNum4Template',
        'reportPager': True,
    },
    'report.num5': {
        'module': 'Bán hàng',
        'name': 'Doanh thu theo nhân viên',
        'reportTemplate': 'ReportNum5Template',
        'tag': 'report_num5_action',
    },
    'report.num6': {
        'module': 'Bán hàng',
        'name': 'Bán - trưng hàng',
        'reportTemplate': 'ReportNum6Template',
        'reportPager': True,
    },
    'report.num7': {
        'module': 'Bán hàng',
        'name': 'Doanh thu tại cửa hàng theo dòng hàng',
        'reportTemplate': 'ReportNum7Template',
        'reportPager': True,
    },
    'report.num8': {
        'module': 'Bán hàng',
        'name': 'Chi tiết hóa đơn áp dụng voucher',
        'reportTemplate': 'ReportNum8Template',
        'reportPager': True,
    },
    'report.num9': {
        'module': 'Bán hàng',
        'name': 'Voucher phát hành',
        'reportTemplate': 'ReportNum9Template',
        'reportPager': True,
    },
    'report.num10': {
        'module': 'Bán hàng',
        'name': 'Lịch sử nâng hạng',
        'reportTemplate': 'ReportNum10Template',
        'reportPager': True,
    },
    'report.num11': {
        'module': 'Bán hàng',
        'name': 'Sắp lên hạng',
        'reportTemplate': 'ReportNum11Template',
        'reportPager': True,
    },
    'report.num12': {
        'module': 'Bán hàng',
        'name': 'Khách hàng không mua hàng',
        'reportTemplate': 'ReportNum12Template',
        'tag': 'report_num12_action',
    },
    'report.num13': {
        'module': 'Mua hàng',
        'name': 'Tình hình thực hiện đơn hàng mua',
        'reportTemplate': 'ReportNum13Template',
        'reportPager': True,
    },
    'report.num14': {
        'module': 'Bán hàng',
        'name': 'Tra cứu mã Code đã sử dụng',
        'reportTemplate': 'ReportNum14Template',
        'reportPager': True,
    },
    'report.num15': {
        'module': 'Bán hàng',
        'name': 'Tra cứu mã Voucher đã sử dụng',
        'reportTemplate': 'ReportNum15Template',
        'reportPager': True,
    },
    'report.num16': {
        'module': 'Kho',
        'name': 'Chi tiết xuất nhập hàng',
        'reportTemplate': 'ReportNum16Template',
        'reportPager': True,
    },
    'report.num17': {
        'module': 'Bán hàng',
        'name': 'Danh sách hóa đơn bán - đổi - trả',
        'reportTemplate': 'ReportNum17Template',
        'tag': 'report_num17_action',
    },
    'report.num18': {
        'module': 'Mua hàng',
        'name': 'Báo cáo chi tiết PR',
        'reportTemplate': 'ReportNum18Template',
        'reportPager': True,
    },
    'report.num19': {
        'module': 'Kho',
        'name': 'Báo cáo tình hình thực hiện yêu cầu chuyển kho',
        'reportTemplate': 'ReportNum19Template',
        'reportPager': True,
    },
    'report.num20': {
        'module': 'Bán hàng',
        'name': 'Bảng kê chi tiết hóa đơn bán - đổi - trả',
        'reportTemplate': 'ReportNum20Template',
        'reportPager': True,
    },
    'report.num21': {
        'module': 'Kho',
        'name': 'Chi tiết hàng hóa luân chuyển',
        'reportTemplate': 'ReportNum21Template',
        'reportPager': True,
    },
    'report.num22': {
        'module': 'Bán hàng',
        'name': 'Báo cáo thu chi tiền mặt tại cửa hàng',
        'reportTemplate': 'ReportNum22Template',
        'tag': 'report_num22_action',
    },
    'report.num23': {
        'module': 'Bán hàng',
        'name': 'Báo cáo giá trị chiết khấu hạng thẻ',
        'reportTemplate': 'ReportNum23Template',
        'reportPager': True,
    },
    'report.num24': {
        'module': 'Bán hàng',
        'name': 'Báo cáo tích - tiêu điểm theo cửa hàng',
        'reportTemplate': 'ReportNum24Template',
        'reportPager': True,
    },
    'report.num25': {
        'module': 'Bán hàng',
        'name': 'Báo cáo dự tính thu nhập nhân viên bán hàng theo doanh thu',
        'reportTemplate': 'ReportNum25Template',
        'reportPager': True,
    },
    'report.num26': {
        'module': 'Kho',
        'name': 'Báo cáo danh sách phiếu điều chuyển',
        'reportTemplate': 'ReportNum26Template',
        'reportPager': True,
    },
    'report.num27': {
        'module': 'Kho',
        'name': 'Báo cáo danh sách phiếu nhập/xuất khác',
        'reportTemplate': 'ReportNum27Template',
        'reportPager': True,
    },
    'report.num28': {
        'module': 'Kho',
        'name': 'Báo cáo danh sách phiếu nhập kho mua hàng',
        'reportTemplate': 'ReportNum28Template',
        'reportPager': True,
    },
    'report.num29': {
        'module': 'Kho',
        'name': 'Báo cáo danh sách CCDC và TSCD',
        'reportTemplate': 'ReportNum29Template',
        'reportPager': True,
    },
    'report.num30': {
        'module': 'Bán hàng',
        'name': 'Bảng kê hàng hóa xuất hóa đơn',
        'reportTemplate': 'ReportNum30Template',
    },
    'report.num31': {
        'module': 'Kho',
        'name': 'Báo cáo template import PO',
        'reportTemplate': 'ReportNum31Template',
        'reportPager': True,
    },
    'report.num32': {
        'module': 'Bán hàng',
        'name': 'Tra cứu thông tin khách hàng',
        'reportTemplate': 'ReportNum32Template',
        'tag': 'report_num32_action',
    },
    'report.num33': {
        'module': 'Bán hàng',
        'name': 'Báo cáo doanh thu sản phẩm',
        'reportTemplate': 'ReportNum33Template',
        'reportPager': True,
    },
    'report.num34': {
        'module': 'Bán hàng',
        'name': 'Danh sách hóa đơn TMĐT',
        'reportTemplate': 'ReportNum34Template',
        'tag': 'report_num34_action',
    },
    'report.num35': {
        'module': 'Bán hàng',
        'name': 'Bảng kê chi tiết hóa đơn TMĐT',
        'reportTemplate': 'ReportNum35Template',
        'reportPager': True,
    },
    'report.num36': {
        'module': 'Kho',
        'name': 'Báo cáo nhập kho thành phẩm sản xuất',
        'reportTemplate': 'ReportNum36Template',
        'reportPager': True,
    },
    'report.num37': {
        'module': 'Kho',
        'name': 'Báo cáo thông tin sản phẩm',
        'reportTemplate': 'ReportNum37Template',
        'reportPager': True,
    },
    'report.num38': {
        'module': 'Kho',
        'name': 'Báo cáo danh sách kho hàng/địa điểm',
        'reportTemplate': 'ReportNum38Template',
        'reportPager': True,
    },
    'report.num39': {
        'module': 'Kho',
        'name': 'Báo cáo chi tiết nhập hàng theo phiếu kho',
        'reportTemplate': 'ReportNum39Template',
        'reportPager': True,
    },
    'report.num40': {
        'module': 'Kho',
        'name': 'Báo cáo tài sản công cụ dụng cụ',
        'reportTemplate': 'ReportNum40Template',
        'reportPager': True,
    },
}
