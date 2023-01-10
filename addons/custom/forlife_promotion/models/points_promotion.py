# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PointsPromotion(models.Model):
    _name = 'points.promotion'
    _description = 'Points Promotion'

    name = fields.Char('Program Name', required=True)
    x_brand_id = fields.Many2one('brand', string='Brand', required=True) # fixme: để tên x_brand_id tránh gây ra lỗi kiểu dữ liệu khi upgrade module, ban đầu khai báo kiểu Char, sẽ điều chỉnh lại thành brand_id vào lần commit code sau
    store_ids = fields.Many2many('store', string='Stores', required=True)
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    first_order = fields.Integer('First Order')
    payment_method_ids = fields.Many2many('pos.payment.method', string='Payment Method', required=True)
    point_expiration = fields.Integer('Point Expiration')
    point_customer_id = fields.Many2one('res.partner', string='Point Customer', required=True)
    acc_accumulate_points_id = fields.Many2one('account.account', string='Account Accumulate Points', required=True)
    acc_reduce_accumulated_points_id = fields.Many2one('account.account', string='Account Reduce Accumulate Points', required=True)
    acc_tax_reduce_accumulated_points_id = fields.Many2one('account.account', string='Account Tax Reduce Accumulate Points', required=True)
    account_journal_id = fields.Many2one('account.journal', string='Account Journal', required=True)
    state = fields.Selection([('new', _('New')), ('in_progress', _('In Progress')), ('finish', _('Finish'))], string='State', default='new')
    value_conversion = fields.Integer('Value Conversion', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    points_product_ids = fields.One2many('points.product', inverse_name='points_promotion_id', string='Points Product')
    event_ids = fields.One2many('event', inverse_name='points_promotion_id', string='Events')

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    def btn_apply(self):
        self.ensure_one()
        res = self.search([('x_brand_id', '=', self.x_brand_id.id), ('state', '=', 'in_progress')])
        if res:
            raise ValidationError(_('The program cannot be executed because the program "%s" is in progress' % res.name))
        self.state = 'in_progress'

    def btn_finish(self):
        self.state = 'finish'

    def check_finish_points_promotion(self):
        res = self.search([('to_date', '<', fields.Datetime.now()), ('state', 'in', ('new', 'in_progress'))])
        if res:
            res.btn_finish()

    def btn_load_all_points_promotion(self):
        self.event_ids.btn_load_points_promotion()
