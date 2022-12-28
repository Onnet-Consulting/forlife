# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Store(models.Model):
    _name = 'store'
    _description = 'Store'

    name = fields.Char('Store Name', required=True)
    code = fields.Char('Store Code', required=True)
    contact_id = fields.Many2one('res.partner', string='Contact', required=True)
    cashier_ids = fields.Many2many('res.users', string='Cashiers', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    brand = fields.Selection([('format', 'Format'), ('tokyolife', 'TokyoLife')], string='Brand', required=True)
    stock_location_id = fields.Many2one('stock.location', string='Location', required=True)
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)
