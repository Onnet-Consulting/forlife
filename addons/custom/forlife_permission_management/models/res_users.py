# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    stock_ids = fields.Many2many('stock.warehouse', string='Stock Warehouse')
    stock_default_id = fields.Many2one('stock.warehouse', string='Stock Warehouse Default')
    brand_ids = fields.Many2many('res.brand', string='Branch')
    brand_default_id = fields.Many2one('res.brand', string='Branch Default')
    department_ids = fields.Many2many('hr.department', string='Department')
    department_default_id = fields.Many2one('hr.department', string='Department Default')
    team_ids = fields.Many2many('hr.team', string='Team')
    team_default_id = fields.Many2one('hr.team', string='Team Default')

