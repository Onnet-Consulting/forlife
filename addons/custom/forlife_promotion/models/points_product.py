# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


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
    product_existed = fields.Text(string='Product Existed', compute='compute_product_existed')
    state_related = fields.Selection('State Related', related='points_promotion_id.state', store=True)
    product_count = fields.Integer('Count product', compute='_compute_product_count')
    _sql_constraints = [
        ('data_uniq', 'unique (points_promotion_id, point_addition, from_date, to_date)', 'The combination of Point Addition, From Date and To Date must be unique !'),
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    def _compute_product_count(self):
        for rec in self:
            rec.product_count = self.env['point.product.model.import'].search_count([('points_product_id', '=', self.id)])

    def action_view_product_point(self):
        ctx = dict(self._context)
        ctx.update({
            'default_points_product_id': self.id,
        })
        return {
            'name': _('Sản phẩm'),
            'domain': [('points_product_id', '=', self.id)],
            'res_model': 'point.product.model.import',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': ctx,
        }
    def _compute_name(self):
        for line in self:
            line.name = _('%s products') % len(line.product_ids)

    def compute_product_existed(self):
        for line in self:
            line.product_existed = json.dumps(line.points_promotion_id.points_product_ids.filtered(lambda f: f.id != line.id).mapped('product_ids.id'))

    def unlink(self):
        for event in self:
            if event.state != "new":
                raise ValidationError(_("You can only delete the new Points Product!"))
        return super().unlink()

    def btn_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Points Product'),
            'res_model': 'points.product',
            'target': 'new',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [[self.env.ref('forlife_promotion.points_product_view_form').id, 'form']],
            'context': dict(self._context),
        }

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
                raise ValidationError(_("The duration of the point product must be within the duration of the program '%s'") % record.points_promotion_id.name)

    def btn_effective(self):
        for line in self:
            if not line.product_ids:
                raise ValidationError(_("Can't activate because product is empty !"))
        self.state = 'effective'
