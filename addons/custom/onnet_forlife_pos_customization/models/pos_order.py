from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    point_order = fields.Integer('Point (+) Order', readonly=True)
    point_event_order = fields.Integer('Point event Order',readonly=True)
    total_point = fields.Integer('Total Point',readonly=True)