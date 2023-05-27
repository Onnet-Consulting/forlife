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
    store_ids = fields.Many2many('store', string='Store')
    store_default_id = fields.Many2one('store', string='Store Default')

    @api.model
    def get_department(self):
        if not self.department_ids:
            department_ids = self.department_ids.search([]).mapped('id')
        else:
            department_ids = (self.department_ids + self.department_default_id).mapped('id')
        return department_ids

    @api.model
    def get_team(self):
        if not self.team_default_id:
            team_ids = self.team_default_id.search([]).mapped('id')
        else:
            team_ids = (self.team_default_id + self.team_ids).mapped('id')
        return team_ids

    @api.model
    def get_company(self):
        if not self.company_ids:
            conpany_ids = self.company_ids.search([]).mapped('id')
        else:
            conpany_ids = (self.company_ids + self.company_id).mapped('id')
        return conpany_ids

    @api.model
    def get_stock(self):
        if not self.stock_ids:
            stock_ids = self.stock_ids.search([]).mapped('id')
        else:
            stock_ids = (self.stock_ids + self.stock_default_id).mapped('id')
        return stock_ids

    @api.model
    def get_brand(self):
        if not self.brand_ids:
            brand_ids = self.brand_ids.search([]).mapped('id')
        else:
            brand_ids = (self.brand_ids + self.brand_default_id).mapped('id')
        return brand_ids

    @api.model
    def get_store(self):
        if not self.store_ids:
            store_ids = self.store_ids.search([]).mapped('id')
        else:
            store_ids = (self.store_ids + self.store_default_id).mapped('id')
        return store_ids

