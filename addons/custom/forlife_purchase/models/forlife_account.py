# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class ForlifeAccount(models.Model):
    _inherit = 'account.move'

    is_check = fields.Boolean()
