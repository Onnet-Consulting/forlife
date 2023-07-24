# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ForlifeAppApiLink(models.Model):
    _name = 'forlife.app.api.link'
    _description = 'App Api Link'

    key = fields.Char('Key', required=True)
    name = fields.Char('Name', required=True)
    value = fields.Char('Value', required=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Name must be unique"),
        ("value_uniq", "unique(value)", "Value must be unique"),
        ("key_uniq", "unique(key)", "Key must be unique")
    ]

