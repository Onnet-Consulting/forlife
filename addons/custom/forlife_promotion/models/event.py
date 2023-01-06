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
    store_ids = fields.Char(string='Stores', required=True)  # fixme Many2many model store định nghĩa trong module forlife_point_of_sale
    customer_conditions = fields.Char(string='Customer Conditions', required=True)  # fixme (many2many) cần phân tích thêm từ phía master data
    value_conversion = fields.Integer('Value Conversion', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective'))], string='State', default='new')
    points_product_ids = fields.One2many('points.product', inverse_name='event_id', string='Points Product')
    is_can_change_points_promotion = fields.Boolean('Can Change Points Promotion', default=False)

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

    @api.constrains('points_promotion_id', 'from_date', 'to_date')
    def _constrains_date(self):
        for record in self:
            if record.points_promotion_id.from_date > record.from_date or record.points_promotion_id.to_date < record.to_date:
                raise ValidationError(_('The duration of the point product must be within the duration of the program "%s"' % record.points_promotion_id.name))

    def btn_effective(self):
        self.state = 'effective'

    def btn_load_points_promotion(self):
        for line in self.filtered(lambda s: s.state == 'new'):
            record = line.points_promotion_id.points_product_ids.filtered(lambda f: f.from_date >= line.from_date and f.to_date <= line.to_date)
            if record:
                record.write({'event_id': line.id})
