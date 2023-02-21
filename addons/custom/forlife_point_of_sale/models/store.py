# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Store(models.Model):
    _name = 'store'
    _description = 'Store'

    name = fields.Char('Store Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    code = fields.Char('Store Code', related='warehouse_id.code', store=True)
    contact_id = fields.Many2one('res.partner', string='Contact Store', required=True)
    cashier_ids = fields.Many2many('res.users', string='Cashiers', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    stock_location_id = fields.Many2one('stock.location', string='Location', required=True)
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)

    @api.constrains('warehouse_id')
    def _check_warehouse_id(self):
        for line in self.filtered(lambda f: f.warehouse_id):
            store = self.search([('id', '!=', line.id), ('warehouse_id', '=', line.warehouse_id.id)])
            if store:
                raise ValidationError(_("Warehouse '%s' has been assigned to store '%s'") % (line.warehouse_id.name, ', '.join(store.mapped('name'))))

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        self.stock_location_id = False

    @api.model
    def get_pos_opened(self, *args, **kwargs):
        query = '''SELECT (SELECT name FROM pos_config WHERE id = ps.config_id) FROM pos_session ps WHERE ps.state = 'opened' AND ps.config_id = %s'''
        config_id = args[0].get("config_id", 0)
        self.env.cr.execute(query, (config_id,))
        data = self.env.cr.fetchall()

        return data
