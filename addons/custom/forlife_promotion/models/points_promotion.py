# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class PointsPromotion(models.Model):
    _name = 'points.promotion'
    _description = 'Points Promotion'
    _order = 'state desc, to_date desc'

    name = fields.Char('Program Name', required=True)
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_ids = fields.Many2many('store', string='Stores')
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    first_order = fields.Integer('First Order', default=0)
    payment_method_ids = fields.Many2many('pos.payment.method', string='Payment Method', required=True)
    point_expiration = fields.Integer('Point Expiration', default=0)
    point_customer_id = fields.Many2one('res.partner', string='Point Customer', required=True)
    acc_accumulate_points_id = fields.Many2one('account.account', string='Account Accumulate Points', required=True)
    acc_reduce_accumulated_points_id = fields.Many2one('account.account', string='Account Reduce Accumulate Points', required=True)
    acc_tax_reduce_accumulated_points_id = fields.Many2one('account.account', string='Account Tax Reduce Accumulate Points', required=True)
    account_journal_id = fields.Many2one('account.journal', string='Account Journal', required=True)
    state = fields.Selection([('new', _('New')), ('in_progress', _('In Progress')), ('finish', _('Finish'))], string='State', default='new')
    value_conversion = fields.Integer('Value Conversion', required=True, default=0)
    point_addition = fields.Integer('Point Addition', required=True, default=0)
    points_product_ids = fields.One2many('points.product', inverse_name='points_promotion_id', string='Points Product')
    event_ids = fields.One2many('event', inverse_name='points_promotion_id', string='Events')
    point_compensate_time = fields.Integer('Point compensate time (day)', default=3)
    point_compensate_rate = fields.Float('Point compensate rate (%)', default=1)

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]


    @api.onchange('brand_id')
    def onchange_brand(self):
        for line in self:
            if line.brand_id:
                line.store_ids = line.store_ids.filtered(lambda f: f.brand_id == line.brand_id)
            else:
                line.store_ids = False

    @api.constrains('from_date', 'to_date')
    def _constrains_date(self):
        for record in self:
            if record.points_product_ids:
                if record.from_date > min(record.points_product_ids.mapped('from_date')) or record.to_date < max(record.points_product_ids.mapped('to_date')):
                    raise ValidationError(_('Invalid program runtime. Please check time on points product tab !'))
            if record.event_ids:
                if record.from_date > min(record.event_ids.mapped('from_date')) or record.to_date < max(record.event_ids.mapped('to_date')):
                    raise ValidationError(_('Invalid program runtime. Please check time on events tab !'))

    def unlink(self):
        for promotion in self:
            if promotion.state != "new" or promotion.event_ids or promotion.points_product_ids.filtered(lambda s: s.state == 'effective'):
                raise ValidationError(_("You can only delete the new points program, no events and points product have not effective!"))
        return super().unlink()

    def btn_apply(self):
        self.ensure_one()
        res = self.search([('brand_id', '=', self.brand_id.id), ('state', '=', 'in_progress')])
        if res:
            raise ValidationError(_("The program cannot be executed because the program '%s' is in progress") % res.name)
        self.state = 'in_progress'

    def btn_finish(self):
        self.state = 'finish'
        self.mapped('event_ids').filtered(lambda f: f.state in ('new', 'effective')).btn_finish()

    def check_finish_points_promotion_and_event(self):
        promotion = self.search([('to_date', '<', fields.Datetime.now()), ('state', 'in', ('new', 'in_progress'))])
        if promotion:
            promotion.btn_finish()
        event = self.env['event'].search([('to_date', '<', fields.Datetime.now()), ('state', 'in', ('new', 'effective'))])
        if event:
            event.btn_finish()

    def btn_load_all_points_promotion(self):
        self.event_ids.btn_load_points_promotion()

    def action_create_points_product(self):
        ctx = dict(self._context)
        ctx.update({
            'default_points_promotion_id': self.id,
            'default_product_existed': json.dumps(self.points_product_ids.mapped('product_ids.id')),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Points Product'),
            'res_model': 'points.product',
            'target': 'new',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_promotion.points_product_view_form').id, 'form']],
            'context': ctx,
        }

    def action_create_events(self):
        ctx = dict(self._context)
        ctx.update({
            'default_points_promotion_id': self.id,
            'default_is_lock_change_points_promotion': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Event'),
            'res_model': 'event',
            'target': 'current',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_promotion.event_view_form').id, 'form']],
            'context': ctx,
        }
