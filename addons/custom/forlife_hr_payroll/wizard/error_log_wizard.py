# -*- coding: utf-8 -*-

from odoo import api, fields, models
import base64


# TODO: can we raise custom exception with log file in the end (on popup) @xmars

class ErrorLogWizard(models.TransientModel):
    _name = 'error.log.wizard'
    _description = 'Error Log Wizard'

    error_file = fields.Binary(attachment=False, string='Error file')
    error_file_name = fields.Char(default='Error.txt')

    def return_error_log(self, error=''):
        error = error or ''
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_hr_payroll.error_log_wizard_action')
        res = self.env['error.log.wizard'].create({'error_file': base64.encodebytes(error.encode())})
        action['res_id'] = res.id
        return action
