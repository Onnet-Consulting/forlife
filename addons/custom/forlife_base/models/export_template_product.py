from odoo import api, fields, models
import copy


class ExportTemplateProduct(models.AbstractModel):
    _name = 'export.template.product'
    _inherit = 'report.base'
    _description = 'Mẫu nhập sản phẩm'

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        self._cr.execute("""
            select json_object_agg(attrs_code, value) as attr_value
            from (select pa.attrs_code,
                         json_agg(concat(pav.code, '~', coalesce(pav.name::json ->> 'vi_VN', pav.name::json ->> 'en_US'))) as value
                  from product_attribute_value pav
                           join product_attribute pa on pav.attribute_id = pa.id
                  group by pa.attrs_code) as x
            """)
        result = self._cr.dictfetchone() or {}
        attr_values = result.get('attr_value') or {}
        attr_codes = self.env['res.utility'].get_attribute_code_config()
        attr_sequences = self.env['res.utility'].get_attribute_sequence_config()
        formats = self.get_format_workbook(workbook)
        template = kwargs.get('template')
        sh_row = 0
        for idx, sheet_name in enumerate(template.sheetnames):
            sheet = workbook.add_worksheet(sheet_name)
            sheet.freeze_panes(1, 0)
            sheet.set_row(0, 40)
            for row, sh_row in enumerate(template.worksheets[idx].iter_rows()):
                for col, cell in enumerate(sh_row):
                    value = cell.value
                    if value is None:
                        continue
                    if row == 0:
                        x_format = formats.get('title_format')
                        if cell.fill.start_color:
                            color = cell.fill.start_color.rgb
                            x_format = formats.get('format_color_' + color) or formats.get('title_format')
                        sheet.write(row, col, value, x_format)
                    elif value and str(value)[:1] == '=':
                        sheet.write_formula(row, col, value, formats.get('normal_format'))
                    else:
                        sheet.write(row, col, value, formats.get('normal_format'))
            sheet.set_column(0, len(sh_row) - 1, 20)
            if idx == 1:
                col = 0
                for attr in attr_sequences:
                    row = 1
                    attr_code = attr_codes.get(attr) or ''
                    attr_value = attr_values.get(attr_code) or []
                    for value in attr_value:
                        val = value.split('~') + ['', '']
                        sheet.write(row, col, val[1], formats.get('normal_format'))
                        sheet.write(row, col + 1, val[0], formats.get('normal_format'))
                        row += 1
                    col += 3

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        normal_format = {
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        }
        format_color1 = copy.copy(normal_format)
        format_color1.update({'bg_color': '#B4C6E7'})

        format_color2 = copy.copy(normal_format)
        format_color2.update({'bg_color': '#92D050'})

        format_color1 = workbook.add_format(format_color1)
        format_color2 = workbook.add_format(format_color2)
        res.update({
            'format_color_FFB4C6E7': format_color1,
            'format_color_FF92D050': format_color2,
        })
        return res
