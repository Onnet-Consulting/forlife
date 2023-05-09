# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PartnerHistoryPointForLife(models.Model):
    _inherit = 'partner.history.point'

    point_order_type = fields.Selection(selection_add=[('coefficient', 'Coefficient')])
    points_coefficient = fields.Integer('Points Coefficient', readonly=True)