# -*- coding: utf-8 -*-

from odoo import api, models, _
from ..fields import *


class HrAssetTransfer(models.Model):
    _inherit = 'hr.asset.transfer'

    def action_approved(self):
        super().action_approved()
        queries = self.hr_asset_transfer_line_ids.bravo_get_insert_sql()
        self.env['hr.asset.transfer.line'].sudo().with_delay().bravo_insert(queries)


class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _inherit = ['hr.asset.transfer.line', 'bravo.model.insert.action']
    _bravo_table = 'B30TransferAsset'

    br1 = BravoCharField(odoo_name='asset_tag', bravo_name='AssetCode')
    br2 = BravoMany2oneField('asset.location', odoo_name='asset_location_to_id', bravo_name='LocationAssetCode',
                             field_detail='code')
    br3 = BravoMany2oneField('hr.employee', odoo_name='employee_to_id', bravo_name='EmployeeCode', field_detail='code')
    br4 = BravoMany2oneField('account.analytic.account', odoo_name='account_analytic_to_id', bravo_name='DeptCode',
                             field_detail='code')
    br5 = BravoIntegerField(odoo_name='id', bravo_name='RowId')
    br6 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='CompanyCode', field_detail='company_id.code')
    br7 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='Stt', field_detail='id')
    br8 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='DocNo',
                             field_detail='name')
    br9 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='DocDate',
                             field_detail='validate_date')

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }
