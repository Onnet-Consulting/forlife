# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Store(models.Model):
    _name = 'store'
    _description = 'Store'

    name = fields.Char('Store Name', required=True, copy=False, default=_('New'))
    code = fields.Char('Store Code', required=True)  # fixme related trường mã kho trong location
    contact_id = fields.Many2one('res.partner', string='Contact', required=True)
    cashier_ids = fields.Many2many('res.users', string='Cashiers', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    x_brand_id = fields.Many2one('brand', string='Brand', required=True) # fixme: để tên x_brand_id tránh gây ra lỗi kiểu dữ liệu khi upgrade module, ban đầu khai báo kiểu Char, sẽ điều chỉnh lại thành brand_id vào lần commit code sau
    stock_location_id = fields.Many2one('stock.location', string='Location', required=True)
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Store name must be unique !'),
    ]

    @api.model
    def get_pos_opened(self):
        query = '''SELECT (SELECT name FROM pos_config WHERE id = ps.config_id) FROM pos_session ps 
            WHERE ps.state = 'opened' 
            AND ps.config_id IN (SELECT pos.id FROM pos_config pos 
                                 WHERE pos.store_id IN (SELECT store_id FROM res_users_store_rel WHERE res_users_id = %s))'''
        self.env.cr.execute(query, (self._uid,))
        data = self.env.cr.fetchall()

        return data
