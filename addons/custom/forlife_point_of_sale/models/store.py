# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Store(models.Model):
    _name = 'store'
    _description = 'Store'

    name = fields.Char('Store Name', required=True)
    code = fields.Char('Store Code', required=True)  # fixme related trường mã kho trong location
    contact_id = fields.Many2one('res.partner', string='Contact', required=True)
    cashier_ids = fields.Many2many('res.users', string='Cashiers', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    stock_location_id = fields.Many2one('stock.location', string='Location', required=True, domain=[('usage', '=', 'internal')])
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)

    @api.model
    def get_pos_opened(self, *args, **kwargs):
        query = '''SELECT (SELECT name FROM pos_config WHERE id = ps.config_id) FROM pos_session ps WHERE ps.state = 'opened' AND ps.config_id = %s'''
        config_id = args[0].get("config_id", 0)
        self.env.cr.execute(query, (config_id,))
        data = self.env.cr.fetchall()

        return data
