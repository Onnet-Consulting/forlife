# -*- coding:utf-8 -*-

from odoo import api, fields, models


class POSReasonRefund(models.Model):
    _name = 'pos.reason.refund'
    _description = 'Reason Refund for POS'

    name = fields.Char('Name', required=True)
    brand_id = fields.Many2one('res.brand', 'Brand', required=True)
