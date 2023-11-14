from odoo import api, fields, models


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
        sheet = workbook.worksheets[1]
        col = 1
        for attr in attr_sequences:
            row = 2
            attr_code = attr_codes.get(attr) or ''
            attr_value = attr_values.get(attr_code) or []
            for value in attr_value:
                val = value.split('~') + ['', '']
                sheet.cell(row, col).value = val[1]
                sheet.cell(row, col + 1).value = val[0]
                row += 1
            col += 3


