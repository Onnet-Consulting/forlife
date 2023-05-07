# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResWard(models.Model):
    _name = 'res.ward'
    _inherit = "forlife.model.mixin"
    _description = "Ward"

    district_id = fields.Many2one('res.state.district', string='District', required=True)
