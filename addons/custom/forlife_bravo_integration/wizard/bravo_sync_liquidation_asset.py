# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class BravoSyncAssetWizard(models.TransientModel):
    _name = 'bravo.sync.asset.wizard'
    _inherit = 'mssql.server'
    _description = 'Bravo synchronize Assets wizard'
