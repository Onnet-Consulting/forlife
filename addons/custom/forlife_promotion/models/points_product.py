from odoo import api, fields, models, _


class PointsProduct(models.Model):
    _name = 'points.product'
    _description = 'Points Product'

    product_tmpl_ids = fields.Many2many('product.template', string='Products')
    point_addition = fields.Integer('Point Addition', required=True)
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    state = fields.Selection([('new', _('New')), ('effective', _('Effective'))], string='State', default='new')
