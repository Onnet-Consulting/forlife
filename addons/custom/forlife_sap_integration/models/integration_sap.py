# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
from requests.auth import HTTPBasicAuth
import logging

_logger = logging.getLogger(__name__)


class IntegrationSap(models.AbstractModel):
    _name = 'integration.sap'
    _description = 'Integration with SAP'

    @api.model
    def get_action_code(self, action_type):
        if action_type == 'add':
            code = 'I'
        elif action_type == 'update':
            code = 'U'
        else:
            code = 'D1'
        return code

    @api.model
    def send_request_to_sap(self, json_body):
        config_params = self.env['ir.config_parameter'].sudo()
        url = config_params.get_param('sap_url')
        username = config_params.get_param('sap_username')
        password = config_params.get_param('sap_password')
        if not url or not username or not password:
            raise UserError(_("Please add SAP connection info to settings!"))
        # FIXME: remove option verify=False in production
        res = requests.post(url, json=json_body, auth=HTTPBasicAuth(username, password), timeout=30, verify=False)
        data = res.json()

        if self.env.context.get('job_uuid'):
            # request run by queue job -> raise Exception so we can know that queue job is failed in some case
            if type(data) is list and any([d for d in data if d.get('type') != 'S']):
                raise Exception(data)
            if type(data) is dict and data.get('type') != 'S':
                raise Exception(data)
        return data

    def sap_update_currency_rate(self, currency_rates):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                "FUNCODE": 107,
                "CommandObject": currency_rates
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't send update currency rate to SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def int10(self, internal_order_codes):
        """Check Internal Order code"""
        try:
            command_object = []
            for idx, io_code in enumerate(internal_order_codes):
                command_object.append({
                    "ZACT": "D2",
                    "ZAUFNR": io_code,
                    "ZKOSTL": ""
                })

            json_body = {
                "FUNCODE": 105,
                "CommandObject": command_object
            }
            io_values = self.send_request_to_sap(json_body)
            return [iv.get('zaufnr') for iv in io_values if iv.get('zaufnr')]
        except Exception as e:
            error_message = str(e)
            _logger.error(error_message)
        return False

    def int07(self, asset_codes, company_code):
        """Check asset codes"""
        try:
            asset_codes = sorted(list(set(asset_codes)))
            commands = []
            for asset_code in asset_codes:
                asset_num = asset_code.split('-')[0]
                asset_sub = asset_code.split('-')[-1]
                value = {
                    "ZACT": "D2",
                    "PARA": f"[ANLN1,EQ,{asset_num}],[ANLN2,EQ,{asset_sub}],[BUKRS,EQ,{company_code}]"
                }
                commands.append(value)
            json_body = {
                "FUNCODE": 104,
                "CommandObject": commands
            }
            assets_value = self.send_request_to_sap(json_body)
            sap_asset_codes = [f"{val.get('anln1')}-{val.get('anln2')}" for val in assets_value]
            return sap_asset_codes
        except Exception as e:
            error_message = str(e)
            _logger.error(error_message)
        return []

    def sap_update_employee(self, employee_values, action_type='add'):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                "FUNCODE": 103,
                "CommandObject": employee_values
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't {action_type} employees on SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def sap_update_products(self, product_values, action_type='add'):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                "FUNCODE": 106,
                "CommandObject": product_values
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't {action_type} products on SAP: \n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def sap_check_sale_debt_limit(self, partner_code, company_code):
        telegram = self.env['integration.telegram']
        command_values = [{
            "ZCODE": partner_code,
            "ZCDRS": company_code
        }]
        try:
            json_body = {
                "FUNCODE": "013",
                "CommandObject": command_values
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't check debt of customers on SAP\n {str(e)}"
            telegram.send_message(error_message)
            return False

    def sap_send_account_moves(self, headers, lines):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                'FUNCODE': '002',
                "Header": headers,
                "Item": lines
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't send journal entries (account.move) to SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def sap_send_reverse_account_moves(self, reverse_values):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                'FUNCODE': '015',
                'CommandObject': reverse_values
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't send reserve journal entries (account.move) to SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def sap_update_partner(self, partner_values, action_type='add'):
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                "FUNCODE": 101,
                "CommandObject": partner_values
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't {action_type} partners on SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)

    def send_pos_journals_file(self, file_name, file_url):
        """Send AWS S3 presigned url (POS journals file) to SAP"""
        telegram = self.env['integration.telegram']
        try:
            json_body = {
                "FUNCODE": "006",
                "CommandObject": [
                    {
                        "URL": file_url
                    }
                ]
            }
            return self.send_request_to_sap(json_body)
        except Exception as e:
            error_message = f"Can't send generated POS journals file {file_name} to SAP\n {str(e)}"
            telegram.send_message(error_message)
            raise Exception(error_message)
