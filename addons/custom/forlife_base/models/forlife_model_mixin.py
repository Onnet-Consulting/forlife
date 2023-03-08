# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ForlifeModelMixin(models.AbstractModel):
    _name = 'forlife.model.mixin'
    _description = 'Forlife Model Mixin'

    code = fields.Char(string="Code", copy=False, required=True)
    name = fields.Char(string="Name", copy=False, required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]
