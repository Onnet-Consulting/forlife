# -*- coding: utf-8 -*-

from odoo import api, models, _
from ..fields import *


class HrAssetTransfer(models.Model):
    _inherit = 'hr.asset.transfer'

    def action_approved(self):
        super().action_approved()
        if self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            queries = self.hr_asset_transfer_line_ids.bravo_get_insert_sql()
            if queries:
                self.env['hr.asset.transfer.line'].sudo().with_delay(channel="root.Bravo").bravo_execute_query(queries)


class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _inherit = ['hr.asset.transfer.line', 'bravo.model.insert.action']
    _bravo_table = 'B30TransferAsset'

    company_id = fields.Many2one('res.company', string='Company')


    br1 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='CompanyCode',
                             field_detail='company_id.code')
    br2 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='Stt', field_detail='id')
    br3 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='DocNo',
                             field_detail='name')
    br4 = BravoMany2oneField('hr.asset.transfer', odoo_name='hr_asset_transfer_id', bravo_name='DocDate',
                             field_detail='validate_date')
    br5 = BravoMany2oneField('assets.assets', odoo_name='asset_code', bravo_name='AssetCode', field_detail="code")
    br6 = BravoMany2oneField('asset.location', odoo_name='asset_location_to_id', bravo_name='LocationAssetCode',
                             field_detail='code')
    br7 = BravoMany2oneField('hr.employee', odoo_name='employee_to_id', bravo_name='EmployeeCode', field_detail='code')
    br8 = BravoMany2oneField('account.analytic.account', odoo_name='account_analytic_to_id', bravo_name='DeptCode',
                             field_detail='code')
    br9 = BravoIntegerField(odoo_name='id', bravo_name='RowId')

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }
