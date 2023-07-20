# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
import json
from .bkav_connector import connect_bkav

_logger = logging.getLogger(__name__)

disable_create_function = False


def get_invoice_identify(self):
    invoice_form = self.invoice_form or ''
    invoice_serial = self.invoice_serial or ''
    invoice_no = self.invoice_no or ''
    return f"[{invoice_form}]_[{invoice_serial}]_[{invoice_no}]"


def get_bkav_config(self):
    return {
        'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
        'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
        'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
        'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
        'cmd_addInvoiceEdit': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit'),
        'cmd_addInvoiceEditDiscount': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit_discount'),
        'cmd_addInvoiceReplace': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_replace'),
        'cmd_updateInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.update_einvoice'),
        'cmd_deleteInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.delete_einvoice'),
        'cmd_cancelInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.cancel_einvoice'),
        'cmd_publishInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.publish_invoice'),
        'cmd_getInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_einvoice'),
        'cmd_getStatusInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_status_einvoice'),
        'cmd_downloadPDF': self.env['ir.config_parameter'].sudo().get_param('bkav.download_pdf'),
        'cmd_downloadXML': self.env['ir.config_parameter'].sudo().get_param('bkav.download_xml')
    }

def getting_invoice_status(self):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_getStatusInvoice')),
        "CommandObject": self.invoice_guid,
    }
    _logger.info(f'BKAV - data get invoice status to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        self.message_post(body=(response.get('Object')))
    else:
        self.data_compare_status = str(response.get('Object'))


def create_invoice_bkav(self,data):
    configs = get_bkav_config(self)
    _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
    data = {
        "CmdType": int(configs.get('cmd_addInvoice')),
        "CommandObject": data,
    }
    _logger.info(f'BKAV - data create invoice to BKAV: {data}')
    try:
        response = connect_bkav(data, configs)
    except Exception as ex:
        _logger.error(f'BKAV connect_bkav: {ex}')
        return False
    if response.get('Status') == 1:
        self.message_post(body=(response.get('Object')))
    else:
        result_data = json.loads(response.get('Object', []))[0]
        try:
            # ghi dữ liệu
            self.write({
                'exists_bkav': True,
                'invoice_guid': result_data.get('InvoiceGUID'),
                'invoice_no': result_data.get('InvoiceNo'),
                'invoice_form': result_data.get('InvoiceForm'),
                'invoice_serial': result_data.get('InvoiceSerial'),
                'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S.%f') if result_data.get('InvoiceDate') else None
            })
            if result_data.get('MessLog'):
                self.message_post(body=result_data.get('MessLog'))
            getting_invoice_status(self)
            publish_invoice_bkav(self)
        except:
            get_invoice_bkav(self)


def publish_invoice_bkav(self):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_publishInvoice')),
        "CommandObject": self.invoice_guid,
    }
    # connect_bkav(data, configs)
    _logger.info(f'BKAV - data publish invoice to BKAV: {data}')
    try:
        response = connect_bkav(data, configs)
    except Exception as ex:
        _logger.error(f'BKAV connect_bkav: {ex}')
        return False
    if response.get('Status') == 1:
        self.message_post(body=(response.get('Object')))
    else:
        self.is_post_bkav = True
        get_invoice_bkav(self)


def update_invoice_bkav(self,data):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_updateInvoice')),
        "CommandObject": data,
    }
    _logger.info(f'BKAV - data update invoice to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        raise ValidationError(response.get('Object'))
    else:
        self.getting_invoice_status()


def get_invoice_bkav(self):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_getInvoice')),
        "CommandObject": self.id
    }
    _logger.info(f'BKAV - data get invoice from BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        self.message_post(body=(response.get('Object')))
    else:
        result_data = json.loads(response.get('Object', {})).get('Invoice', {})
        self.write({
            'data_compare_status': str(result_data.get('InvoiceStatusID')),
            'exists_bkav': True,
            'invoice_guid': result_data.get('InvoiceGUID'),
            'invoice_no': result_data.get('InvoiceNo'),
            'invoice_form': result_data.get('InvoiceForm'),
            'invoice_serial': result_data.get('InvoiceSerial'),
            'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S') if result_data.get('InvoiceDate') else None,
            'invoice_state_e': str(result_data.get('InvoiceStatusID'))
        })


def cancel_invoice_bkav(self):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_cancelInvoice')),
        "CommandObject": [
            {
                "Invoice": {
                    "InvoiceGUID": self.invoice_guid,
                    "Reason": "Hủy vì sai sót"
                },
                "PartnerInvoiceID": self.id,
            }
        ]
    }
    _logger.info(f'BKAV - data cancel invoice to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        raise ValidationError(response.get('Object'))
    else:
        self.is_check_cancel = True
        getting_invoice_status(self)


def delete_invoice_bkav(self):
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_deleteInvoice')),
        "CommandObject": [
            {
                "Invoice": {
                    "InvoiceGUID": self.invoice_guid,
                    "Reason": "Xóa vì sai sót"
                },
                "PartnerInvoiceID": self.id,
            }
        ]
    }
    _logger.info(f'BKAV - data delete invoice to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        raise ValidationError(response.get('Object'))


def download_invoice_bkav(self):
    if not self.eivoice_file:
        configs = get_bkav_config(self)
        data = {
            "CmdType": int(configs.get('cmd_downloadPDF')),
            "CommandObject": self.invoice_guid,
        }
        _logger.info(f'BKAV - data download invoice to BKAV: {data}')
        response_action = connect_bkav(data, configs)
        if response_action.get('Status') == '1':
            self.message_post(body=(response_action.get('Object')))
        else:
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"{self.invoice_no}.pdf",
                'datas': json.loads(response_action.get('Object')).get('PDF', ''),
            })
            self.eivoice_file = attachment_id
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                        % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'self',
            }
    else:
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                    % (self.eivoice_file.id, self.eivoice_file.name),
            'target': 'self',
        }
