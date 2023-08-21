# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ReportNum1(models.TransientModel):
    _name = 'report.num1'
    _inherit = 'report.base'
    _description = 'Report revenue by product'
