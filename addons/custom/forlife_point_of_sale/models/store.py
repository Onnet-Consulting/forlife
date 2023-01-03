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
    brand = fields.Selection([('format', 'Format'), ('tokyolife', 'TokyoLife')], string='Brand', required=True)
    stock_location_id = fields.Many2one('stock.location', string='Location', required=True)
    pos_config_ids = fields.One2many('pos.config', 'store_id', string='POS Config', readonly=True)
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method', required=True)

    @api.model
    def retrieve_dashboard(self):
        self.check_access_rights('read')

        query = '''with tb as (
                        select ps.config_id, rp.name from pos_session ps
                         join res_users ru on ru.id = ps.user_id
                         join res_partner rp on rp.id = ru.partner_id
                         where state = 'opened'
                    )
                    select pos.name, store.name, tb.name from pos_config pos
                    join store on pos.store_id = store.id
                    join tb on tb.config_id = pos.id
                    where pos.store_id in 
                        (select store_id from res_users_store_rel where res_users_id = %s)'''
        self.env.cr.execute(query, (self._uid,))
        data = self.env.cr.fetchall()
        group = {}
        res = []
        for i in data:
            group.update({i[1]: group.get(i[1], []) + [i[0] + _(' opened by ') + i[2]]})
        for k, v in group.items():
            res.append(_('Store ') + k + ': ' + ', '.join(v))
        return dict(data='; '.join(res))
