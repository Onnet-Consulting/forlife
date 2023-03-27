# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CostCenter(models.Model):
    _name = 'cost.center'
    _description = "Cost center"
    _rec_name = 'code'

    name = fields.Char("Name")
    code = fields.Char("Code")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
