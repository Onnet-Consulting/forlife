# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    store_ids = fields.Many2many('store', string='Stores', required=True)
    customer_conditions = fields.Char(string='Customer Conditions', required=True)  # fixme (many2many) cần phân tích thêm từ phía master data
    value_conversion = fields.Integer('Value Conversion', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective'))], string='State', default='new')
    points_product_ids = fields.One2many('points.product.line', 'event_id', string='Points Product')
    is_lock_change_points_promotion = fields.Boolean('Lock Change Points Promotion', default=False)

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

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
                raise ValidationError(_('The duration of the events must be within the duration of the program "%s"' % record.points_promotion_id.name))

    def unlink(self):
        for event in self:
            if event.state != "new":
                raise ValidationError(_("You can only delete the new Event!"))
        return super().unlink()

    def btn_effective(self):
        self.state = 'effective'

    def btn_load_points_promotion(self):
        for line in self.filtered(lambda s: s.state == 'new'):
            record = line.points_promotion_id.points_product_ids.filtered(lambda f: f.from_date <= line.from_date and f.to_date >= line.to_date)
            _id = []
            for rec in record:
                res = line.points_product_ids.filtered(lambda x: x.points_product_id == rec)
                if res:
                    _id.append(res.id)
                else:
                    new_line = self.env['points.product.line'].create({
                        'points_product_id': rec.id,
                        'event_id': line.id,
                        'point_addition': rec.point_addition,
                    })
                    _id.append(new_line.id)
            _remove = line.points_product_ids.filtered(lambda xx: xx.id not in _id)
            if _remove:
                _remove.unlink()
