# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ReportNum3(models.TransientModel):
    _name = 'report.num3'
    _inherit = 'report.base'
    _description = 'Report stock in time range by warehouse'
