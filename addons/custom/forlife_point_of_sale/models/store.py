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
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    start_date = fields.Date('Start Date')
    opening_time = fields.Float('Opening time', default=8.5)
    closing_time = fields.Float('Closing time', default=22.0)
    active = fields.Boolean(string='Lưu trữ', default=True)

    @api.constrains('warehouse_id')
    def _check_warehouse_id(self):
        for line in self.filtered(lambda f: f.warehouse_id):
            store = self.search([('id', '!=', line.id), ('warehouse_id', '=', line.warehouse_id.id)])
            if store:
                raise ValidationError(_("Warehouse '%s' has been assigned to store '%s'") % (line.warehouse_id.name, ', '.join(store.mapped('name'))))

    @api.constrains('opening_time', 'closing_time')
    def _check_time(self):
        for line in self:
            if line.opening_time < 0 or line.opening_time > 24.0 or line.closing_time < 0 or line.closing_time > 24.0:
                raise ValidationError(_('Opening/closing time should be between 0 and 24'))
            if line.opening_time >= line.closing_time:
                raise ValidationError(_('Opening time must be less than closing time'))
