# -*- encoding: utf-8 -*-

def get_style(wb):
    style_title = wb.add_format(
        {'font_size': '20', 'font_name': 'Times New Roman', 'bold': True, 'align': 'center', 'valign': 'vcenter'})

    style_header_unbold = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'align': 'center', 'valign': 'vcenter'})

    style_header_bold = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'bold': True, 'align': 'center', 'valign': 'vcenter'})

    style_header_bold_border = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'bold': True, 'align': 'center', 'valign': 'vcenter',
         'border': True})

    # data
    style_right_data_float = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'align': 'right', 'valign': 'vcenter',
         'num_format': '#,##0.00', 'border': True})
    style_right_data_int = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'align': 'right', 'valign': 'vcenter',
         'num_format': '#,##0', 'border': True})
    style_left_data_string_border = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'align': 'left', 'valign': 'vcenter', 'border': True})

    style_left_data_string = wb.add_format(
        {'font_size': '12', 'font_name': 'Times New Roman', 'align': 'left', 'valign': 'vcenter'})
    return {
        'style_title': style_title,
        'style_header_unbold': style_header_unbold,
        'style_header_bold': style_header_bold,
        'style_header_bold_border': style_header_bold_border,
        'style_right_data_float': style_right_data_float,
        'style_right_data_int': style_right_data_int,
        'style_left_data_string': style_left_data_string,
        'style_left_data_string_border': style_left_data_string_border,
    }
