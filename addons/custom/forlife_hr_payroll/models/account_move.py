# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ref2 = fields.Char(string='Reference #2', copy=False)
    salary_record_id = fields.Many2one('salary.record', string='Salary record', ondelete='restrict')
    # FIXME: after add 'forlife_invoice' module to depends section in manifest file of this module, remove x_asset_fin field  below
    x_asset_fin = fields.Selection([
        ('TC', 'TC'),
        ('QC', 'QC'),
    ], string='Phân loại tài chính')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_id = fields.Many2one('assets.assets', string='Project Code')
    # FIXME: after add 'forlife_invoice' module to depends section in manifest file of this module, remove work_order field  below
    work_order = fields.Many2one('forlife.production', string='Production order')
    occasion_code_id = fields.Many2one('occasion.code', string='Internal Order Code')

    # FIXME: delete project_code, manufacture_order_code, internal_order_code fields below
    project_code = fields.Char(string='Project Code')
    manufacture_order_code = fields.Char(string='Manufacture Order Code')
    internal_order_code = fields.Char(string='Internal Order Code')
