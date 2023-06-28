# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectiveStore(models.Model):
    _name = 'business.objective.store'
    _description = 'Business objective store'
    _rec_name = 'bo_plan_id'
    _order = 'bo_plan_id desc'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict', required=True)
    store_id = fields.Many2one('store', 'Store', ondelete='restrict', required=True)
    revenue_target = fields.Monetary('Revenue target')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)
