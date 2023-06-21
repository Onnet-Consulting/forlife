# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class Event(models.Model):
    _name = 'event'
    _description = 'Event'

    points_promotion_id = fields.Many2one('points.promotion', string='Points Promotion', required=True)
    name = fields.Char('Event Name', required=True)
    from_date = fields.Datetime('From Date', required=True)
    to_date = fields.Datetime('To Date', required=True)
    month_ids = fields.Many2many('month.data', string='Months')
    dayofmonth_ids = fields.Many2many('dayofmonth.data', string='DayOfMonth')
    dayofweek_ids = fields.Many2many('dayofweek.data', string='DayOfWeek')
    hour_ids = fields.Many2many('hour.data', string='Hours')
    store_ids = fields.Many2many('store', string='Stores')
    customer_conditions = fields.Char(string='Customer Conditions')
    value_conversion = fields.Integer('Value Conversion', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective')), ('finish', _('Finish'))], string='State', default='new')
    points_product_ids = fields.One2many('points.product.line', 'event_id', string='Points Product')
    is_lock_change_points_promotion = fields.Boolean('Lock Change Points Promotion', default=False)
    points_product_existed = fields.Text(string='Points Product Existed', default='[]')
    brand_id = fields.Many2one('res.brand', string='Brand', related='points_promotion_id.brand_id', store=False)
    # partner_ids = fields.Many2many('res.partner',string='Danh sách khách hàng')
    partner_count = fields.Integer(string='Count partner', compute='_compute_list_partner')

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    # new action for import
    def _compute_list_partner(self):
        for rec in self:
            rec.partner_count = self.env['contact.event.follow'].search_count([('event_id', '=', self.id)])

    def action_view_partner(self):
        ctx = dict(self._context)
        ctx.update({
            'default_event_id': self.id,
        })
        return {
            'name': _('Khách hàng'),
            'domain': [('event_id', '=', self.id)],
            'res_model': 'contact.event.follow',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': ctx,
        }

    # new action for import

    @api.onchange('points_promotion_id')
    def onchange_points_promotion(self):
        for line in self:
            if line.points_promotion_id:
                line.from_date = line.points_promotion_id.from_date
                line.to_date = line.points_promotion_id.to_date
                line.value_conversion = line.points_promotion_id.value_conversion
                line.point_addition = line.points_promotion_id.point_addition
                line.store_ids = line.points_promotion_id.store_ids

    @api.constrains('points_promotion_id', 'from_date', 'to_date')
    def _constrains_date(self):
        for record in self:
            if record.points_promotion_id.from_date > record.from_date or record.points_promotion_id.to_date < record.to_date:
                raise ValidationError(_('The duration of the events must be within the duration of the program "%s"') % record.points_promotion_id.name)

    def unlink(self):
        for event in self:
            if event.state != "new" or event.points_product_ids.filtered(lambda s: s.state == 'effective'):
                raise ValidationError(_("You can only delete the new Event and points product have not effective!"))
        return super().unlink()

    def btn_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Event'),
            'res_model': 'event',
            'target': 'current',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [[self.env.ref('forlife_promotion.event_view_form').id, 'form']],
            'context': dict(self._context),
        }

    def btn_effective(self):
        self.state = 'effective'

    def btn_finish(self):
        self.state = 'finish'

    def btn_load_points_promotion(self):
        for line in self.filtered(lambda s: s.state in ('new', 'effective')):
            if line.state == 'new':
                line.load_by_state_new()
            else:
                line.load_by_state_effective()

    def load_by_state_new(self):
        points_products = self.points_promotion_id.points_product_ids.filtered(lambda f: f.from_date <= self.from_date and f.to_date >= self.to_date)
        for rec in points_products:
            res = self.points_product_ids.filtered(lambda x: x.points_product_id == rec)
            if res:
                if res.state == 'new':
                    res.product_ids = rec.product_ids
            else:
                self.env['points.product.line'].create({
                    'points_product_id': rec.id,
                    'event_id': self.id,
                    'point_addition': rec.point_addition,
                    'product_ids': [(6, 0, rec.product_ids.ids)],
                })
        if points_products:
            self.write({'points_product_existed': json.dumps(points_products.ids)})

    def load_by_state_effective(self):
        points_product_existed = list(set((json.loads(self.points_product_existed) or []) + self.points_product_ids.mapped('points_product_id').ids))
        points_products = self.points_promotion_id.points_product_ids.filtered(lambda f: f.from_date <= self.from_date and f.to_date >= self.to_date and f.id not in points_product_existed)
        for rec in points_products:
            self.env['points.product.line'].create({
                'points_product_id': rec.id,
                'event_id': self.id,
                'point_addition': rec.point_addition,
                'product_ids': [(6, 0, rec.product_ids.ids)],
            })
        if points_products:
            self.write({'points_product_existed': json.dumps(points_products.ids + points_product_existed)})
