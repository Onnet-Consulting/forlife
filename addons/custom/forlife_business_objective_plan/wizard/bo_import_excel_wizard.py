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
        for line in values:
            print(line[0], line[1], line[2])
        # return self.return_error_log('ok')

    def _import_bo_employee(self, values):
        sale_provinces = self.env['res.sale.province'].search_read([], ['code'])
        stores = self.env['store'].search_read([('brand_id', '=', self.bo_plan_id.brand_id.id)], ['code'])
        for line in values:
            print(line[0], line[1], line[2], line[3], line[4])
        # return self.return_error_log('ok')

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('forlife_business_objective_plan.bo_import_excel_wizard_action').read()[0]
        action['res_id'] = self.id
        return action
