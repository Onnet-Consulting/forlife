# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResBrand(models.Model):
    _name = 'res.brand'
    _description = 'Brand'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Brand code must be unique !'),
    ]

    def name_get(self):
        result = []
        for br in self:
            if br.code:
                name = f'[{br.code}]{br.name}'
            else:
                name = f'{br.name}'
            result.append((br.id, name))
        return result
