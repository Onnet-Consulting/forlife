# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PointsProduct(models.Model):
    _name = 'points.product'
    _description = 'Points Product'

    name = fields.Char('Name', compute='_compute_name')
    points_promotion_id = fields.Many2one('points.promotion', string='Points Promotion', ondelete='cascade')
    product_ids = fields.Many2many('product.product', string='Products')
    point_addition = fields.Integer('Point Addition', required=True)
    from_date = fields.Datetime('From Date', required=True)
    to_date = fields.Datetime('To Date', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective'))], string='State', default='new')

    _sql_constraints = [
        ('data_uniq', 'unique (points_promotion_id, point_addition, from_date, to_date)', 'The combination of Point Addition, From Date and To Date must be unique !'),
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    def _compute_name(self):
        for line in self:
            line.name = _('%s products') % len(line.product_ids)

    @api.onchange('points_promotion_id')
    def onchange_points_promotion(self):
        for line in self:
            if line.points_promotion_id:
                line.from_date = line.points_promotion_id.from_date
                line.to_date = line.points_promotion_id.to_date

    @api.constrains('points_promotion_id', 'from_date', 'to_date')
    def _constrains_date(self):
        for record in self:
            if record.points_promotion_id.from_date > record.from_date or record.points_promotion_id.to_date < record.to_date:
                raise ValidationError(_('The duration of the point product must be within the duration of the program "%s"' % record.points_promotion_id.name))

    def btn_effective(self):
        self.state = 'effective'
