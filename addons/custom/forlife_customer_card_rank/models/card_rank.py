# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CardRank(models.Model):
    _name = 'card.rank'
    _description = 'Card Rank'

    name = fields.Char('Program Name', required=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Rank name must be unique"),
    ]
