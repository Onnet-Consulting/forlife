# -*- coding: utf-8 -*-

from odoo import api, models, _

class HrAssetTransferLine(models.Model):
    _name = 'hr.asset.transfer.line'
    _inherit = ['hr.asset.transfer.line', 'bravo.model']
    _bravo_table = 'B30TransferAsset'

