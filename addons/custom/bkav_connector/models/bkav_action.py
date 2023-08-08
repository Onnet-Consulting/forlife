# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from datetime import datetime
import json
from .bkav_connector import connect_bkav
import logging
_logger = logging.getLogger(__name__)


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


def get_invoice_identify(self):
    invoice_form = self.invoice_form or ''
    invoice_serial = self.invoice_serial or ''
    invoice_no = self.invoice_no or ''
    return f"[{invoice_form}]_[{invoice_serial}]_[{invoice_no}]"


def get_invoice_status(self):
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
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
        self._compute_data_compare_status()


def create_invoice_bkav(self,data,is_publish=True,origin_id=False,issue_invoice_type=''):
    configs = get_bkav_config(self)
    _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
    CmdType = int(configs.get('cmd_addInvoice'))
    if issue_invoice_type:
        if issue_invoice_type in ('adjust', 'replace') and (not origin_id or not origin_id.invoice_no):
            raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh hoặc thay thế')
        if issue_invoice_type == 'adjust':
            CmdType = int(configs.get('cmd_addInvoiceEdit'))
        elif issue_invoice_type == 'replace':
            CmdType = int(configs.get('cmd_addInvoiceReplace'))

    data = {
        "CmdType": CmdType,
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
                'invoice_e_date': (datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S.%f')).date() if result_data.get('InvoiceDate') else None
            })
            if result_data.get('MessLog'):
                self.message_post(body=result_data.get('MessLog'))
            if is_publish:
                publish_invoice_bkav(self)
            get_invoice_bkav(self)
            get_invoice_status(self)
        except:
            get_invoice_bkav(self)
            get_invoice_status(self)


def publish_invoice_bkav(self):
    if self.is_post_bkav:
        return
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_publishInvoice')),
        "CommandObject": self.invoice_guid,
    }
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
        get_invoice_status(self)


def update_invoice_bkav(self,data):
    if self.is_post_bkav:
        return
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
        get_invoice_bkav(self)
        get_invoice_status(self)


def get_invoice_bkav(self):
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_getInvoice')),
        "CommandObject": self.invoice_guid
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
            'invoice_e_date': (datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S').date()) if result_data.get('InvoiceDate') else None,
        })
        get_invoice_status(self)


def cancel_invoice_bkav(self):
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
    is_publish = False
    if self.is_post_bkav:
        is_publish = True
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_cancelInvoice')),
        "CommandObject": [
            {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "Reason": "Hủy vì sai sót"
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": self.invoice_guid
            }
        ]
    }
    _logger.info(f'BKAV - data cancel invoice to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        raise ValidationError(response.get('Object'))
    else:
        self.is_check_cancel = True
        if is_publish:
            publish_invoice_bkav(self)
        get_invoice_bkav(self)
        get_invoice_status(self)


def delete_invoice_bkav(self,):
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
    configs = get_bkav_config(self)
    data = {
        "CmdType": int(configs.get('cmd_deleteInvoice')),
        "CommandObject": [
            {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "Reason": "Xóa vì sai sót"
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": self.invoice_guid
            }
        ]
    }
    _logger.info(f'BKAV - data delete invoice to BKAV: {data}')
    response = connect_bkav(data, configs)
    if response.get('Status') == 1:
        raise ValidationError(response.get('Object'))


def download_invoice_bkav(self):
    if not self.invoice_guid or self.invoice_guid == '00000000-0000-0000-0000-000000000000':
        return
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
