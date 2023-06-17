# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bkav_url = fields.Char(string='BKAV URL', config_parameter='bkav.url')
    bkav_partner_token = fields.Char(string='Partner Token', config_parameter='bkav.partner_token')
    bkav_partner_guid = fields.Char(string='Partner GUID', config_parameter='bkav.partner_guid')
    bkav_add_einvoice = fields.Char(string='Mã tạo HD', config_parameter='bkav.add_einvoice')
    bkav_add_einvoice_replace = fields.Char(string='Mã tạo HD thay thế', config_parameter='bkav.add_einvoice_replace')
    bkav_add_einvoice_edit = fields.Char(string='Mã tạo HD điều chỉnh', config_parameter='bkav.add_einvoice_edit')
    bkav_add_einvoice_edit_discount = fields.Char(string='Mã tạo HD điều chỉnh chiết khấu', config_parameter='bkav.add_einvoice_edit_discount')
    bkav_update_einvoice = fields.Char(string='Mã cập nhật hóa đơn', config_parameter='bkav.update_einvoice')
    bkav_delete_einvoice = fields.Char(string='Mã xóa hóa đơn', config_parameter='bkav.delete_einvoice')
    bkav_cancel_einvoice = fields.Char(string='Mã hủy hóa đơn', config_parameter='bkav.cancel_einvoice')
    bkav_get_einvoice = fields.Char(string='Mã lấy chi tiết hóa đơn', config_parameter='bkav.get_einvoice')
    bkav_get_status_einvoice = fields.Char(string='Mã lấy trạng thái hóa đơn', config_parameter='bkav.get_status_einvoice')
    bkav_download_pdf = fields.Char(string='Mã Download pdf', config_parameter='bkav.download_pdf')
    bkav_download_xml = fields.Char(string='Mã Download xml', config_parameter='bkav.download_xml')

    # bkav_get_invoice_by_id = fields.Char(string='Get invoice by id', config_parameter='bkav.get_invoice_by_id')
    # bkav_search_einvoice = fields.Char(string='Search e invoice', config_parameter='bkav.search_einvoice')
    # bkav_get_availiable_serial = fields.Char(string='Get availiable serial', config_parameter='bkav.get_availiable_serial')
    # bkav_publish_invoice = fields.Char(string='Publish invoice', config_parameter='bkav.publish_invoice')
    # bkav_get_status_invoices = fields.Char(string='Get status invoices', config_parameter='bkav.get_status_invoices')
    # bkav_invoice_business = fields.Char(string='Invoice business', config_parameter='bkav.invoice_business')
