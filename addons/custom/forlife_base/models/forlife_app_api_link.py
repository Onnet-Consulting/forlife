# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ForlifeAppApiLink(models.Model):
    _name = 'forlife.app.api.link'
    _inherit = 'res.general.info'
    _description = 'App Api Link'

    key = fields.Char('Key', required=True)

    _sql_constraints = [
        ("key_uniq", "unique(key)", "Key must be unique"),
    ]
