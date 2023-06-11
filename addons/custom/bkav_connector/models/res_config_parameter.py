# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bkav_token_create = fields.Char(string='Api Token Create', config_parameter='bkav.token_create')
    bkav_email = fields.Char(string='Email', config_parameter='bkav.email')
    bkav_password = fields.Char(string='Password', config_parameter='bkav.password')
    bkav_add_einvoice = fields.Char(string='Add e invoice', config_parameter='bkav.add_einvoice')
    bkav_update_einvoice = fields.Char(string='Update e invoice', config_parameter='bkav.update_einvoice')
    bkav_get_invoice_by_id = fields.Char(string='Get invoice by id', config_parameter='bkav.get_invoice_by_id')
    bkav_delete_einvoice = fields.Char(string='Delete e invoice', config_parameter='bkav.delete_einvoice')
    bkav_search_einvoice = fields.Char(string='Search e invoice', config_parameter='bkav.search_einvoice')
    bkav_get_availiable_serial = fields.Char(string='Get availiable serial', config_parameter='bkav.get_availiable_serial')
    bkav_publish_invoice = fields.Char(string='Publish invoice', config_parameter='bkav.publish_invoice')
    bkav_get_status_invoices = fields.Char(string='Get status invoices', config_parameter='bkav.get_status_invoices')
    bkav_download_invoice_as_pdf = fields.Char(string='Download invoice as pdf', config_parameter='bkav.download_invoice_as_pdf')
    bkav_download_invoice_as_xml = fields.Char(string='Download invoice as xml', config_parameter='bkav.download_invoice_as_xml')
    bkav_invoice_business = fields.Char(string='Invoice business', config_parameter='bkav.invoice_business')
