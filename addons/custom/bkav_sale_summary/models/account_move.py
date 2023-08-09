# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from . import bkav_action
from odoo.exceptions import ValidationError


class AccountMoveBKAV(models.Model):
    _inherit = 'account.move'

    is_synthetic = fields.Boolean(string='Synthetic', default=False, copy=False)

