from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    point_addition = fields.Integer('Point(+)')
    point_event = fields.Integer('Point Event')