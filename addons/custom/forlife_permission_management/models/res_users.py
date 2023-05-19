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

    @api.model
    def get_department(self):
        if not self.department_ids:
            department_ids = self.department_ids.search([]).mapped('id')
        else:
            department_ids = self.department_ids.mapped('id')
        return department_ids

    @api.model
    def get_team(self):
        if not self.x_studio_many2one_field_AkIph:
            team_ids = self.x_studio_many2one_field_AkIph.search([]).mapped('id')
        else:
            team_ids = self.x_studio_many2one_field_AkIph.mapped('id')
        return team_ids

    @api.model
    def get_company(self):
        if not self.conpany_ids:
            conpany_ids = self.conpany_ids.search([]).mapped('id')
        else:
            conpany_ids = self.conpany_ids.mapped('id')
        return conpany_ids

    @api.model
    def get_stock(self):
        if not self.stock_ids:
            stock_ids = self.stock_ids.search([]).mapped('id')
        else:
            stock_ids = self.stock_ids.mapped('id')
        return stock_ids


