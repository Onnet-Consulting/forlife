# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64
import re


class BoImportExcelWizard(models.TransientModel):
    _name = 'bo.import.excel.wizard'
    _description = 'Import BO'

    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Error file')
    error_file_name = fields.Char(default='Error.txt')

    def download_template_file(self):
        attachment_id = self.env.ref(f'forlife_business_objective_plan.{self._context.get("template_xml_id")}')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    def action_import(self):
        pass
