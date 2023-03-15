# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class PointsProductLine(models.Model):
    _name = 'points.product.line'
    _description = 'Points Product Line'

    points_product_id = fields.Many2one('points.product', string='Points Product Key', required=True, ondelete='restrict')
    name = fields.Char('Product', compute='_compute_name')
    event_id = fields.Many2one('event', string='Event', ondelete='cascade')
    product_ids = fields.Many2many('product.product', string='Products')
    point_addition = fields.Integer('Point Additions', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective'))], string='State', default='new')
    product_existed = fields.Text(string='Product Existed', compute='compute_product_existed')
    state_related = fields.Selection('State Related', related='event_id.state', store=True)

    def _compute_name(self):
        for line in self:
            line.name = _('%s products') % len(line.product_ids)

    def compute_product_existed(self):
        for line in self:
            line.product_existed = json.dumps(line.event_id.points_product_ids.filtered(lambda f: f.id != line.id).mapped('product_ids.id'))

    def unlink(self):
        for event in self:
            if event.state != "new":
                raise ValidationError(_("You can only delete the new Points Product!"))
        return super().unlink()

    def btn_effective(self):
        for line in self:
            if not line.product_ids:
                raise ValidationError(_("Can't activate because product is empty !"))
        self.state = 'effective'

    def btn_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Points Product'),
            'res_model': 'points.product.line',
            'target': 'new',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [[self.env.ref('forlife_promotion.points_product_line_view_form').id, 'form']],
            'context': dict(self._context),
        }
