# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64


class BoImportExcelWizard(models.TransientModel):
    _name = 'bo.import.excel.wizard'
    _description = 'Import BO'

    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Error file')
    error_file_name = fields.Char(default='Error.txt')
    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan')

    def download_template_file(self):
        attachment_id = self.env.ref(f'forlife_business_objective_plan.{self._context.get("template_xml_id")}')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError(_("Please upload file template before click Import button !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        values = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        return getattr(self, self._context.get('template_xml_id').replace('template', ''), None)(values)

    def _import_bo_store(self, values):
        brand_id = self.bo_plan_id.brand_id
        store_exist = self.bo_plan_id.bo_store_ids.store_id.ids
        self._cr.execute(f"""
select (select json_object_agg(code, id) from res_sale_province)                                    as sale_province,
       (select json_object_agg(code, id) from store where brand_id = {brand_id.id}) as store
""")
        data = self._cr.dictfetchone()
        sale_provinces = data.get('sale_province') or {}
        stores = data.get('store') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            sale_province_id = sale_provinces.get(val[0])
            store_id = stores.get(val[1])
            if not sale_province_id:
                error.append(f"Dòng {index + 1}, không tìm thấy khu vực có mã là '{val[0]}'")
            if not store_id:
                error.append(f"Dòng {index + 1}, không tìm thấy cửa hàng thuộc thương hiệu '{brand_id.name}' có mã là '{val[1]}'")
            if store_id in store_exist:
                error.append(f"Dòng {index + 1}, cửa hàng có mã là '{val[1]}' đã tồn tại trong phiếu '{self.bo_plan_id.name}'")
            if not error:
                vals.append({
                    'bo_plan_id': self.bo_plan_id.id,
                    'brand_id': brand_id.id,
                    'sale_province_id': sale_province_id,
                    'store_id': store_id,
                    'revenue_target': int(val[2]),
                })
        if error:
            return self.return_error_log('\n'.join(error))
        if vals:
            self.env['business.objective.store'].create(vals)
        return self.bo_plan_id.open_business_objective()

    def _import_bo_employee(self, values):
        brand_id = self.bo_plan_id.brand_id
        self._cr.execute(f"""
select (select json_object_agg(code, id) from res_sale_province)                                   as sale_province,
       (select json_object_agg(code, id) from store where brand_id = {brand_id.id})                as store,
       (select json_object_agg(code, id) from hr_employee where code notnull)                      as employee,
       (select json_object_agg(coalesce(name::json ->> 'vi_VN', name::json ->> 'en_US'), id)
        from hr_job where name notnull and company_id = any(array{self._context.get('allowed_company_ids') or [-1]})) as job
""")
        data = self._cr.dictfetchone()
        sale_provinces = data.get('sale_province') or {}
        stores = data.get('store') or {}
        employees = data.get('employee') or {}
        jobs = data.get('job') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            sale_province_id = sale_provinces.get(val[0])
            store_id = stores.get(val[1])
            employee_id = employees.get(val[2])
            job_id = jobs.get(val[3])

            if not sale_province_id:
                error.append(f"Dòng {index + 1}, không tìm thấy khu vực có mã là '{val[0]}'")
            if not store_id:
                error.append(f"Dòng {index + 1}, không tìm thấy cửa hàng thuộc thương hiệu '{brand_id.name}' có mã là '{val[1]}'")
            if not employee_id:
                error.append(f"Dòng {index + 1}, không tìm thấy nhân viên có mã là '{val[2]}'")
            if not job_id:
                error.append(f"Dòng {index + 1}, không tìm thấy vị trí công việc có tên là '{val[3]}'")
            if val[4]:
                concurrent_position_id = jobs.get(val[4])
                if not concurrent_position_id:
                    error.append(f"Dòng {index + 1}, không tìm thấy vị trí kiêm nhiệm có tên là '{val[4]}'")
            if not error:
                vals.append({
                    'bo_plan_id': self.bo_plan_id.id,
                    'brand_id': brand_id.id,
                    'sale_province_id': sale_province_id,
                    'store_id': store_id,
                    'employee_id': employee_id,
                    'job_id': job_id,
                    'revenue_target': int(val[5]),
                })
        if error:
            return self.return_error_log('\n'.join(error))
        if vals:
            self.env['business.objective.employee'].create(vals)
        return self.bo_plan_id.open_business_objective()

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('forlife_business_objective_plan.bo_import_excel_wizard_action').read()[0]
        action['res_id'] = self.id
        return action
