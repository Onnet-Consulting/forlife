# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def create_and_read(self, vals_list, read_fields=None):
        if not read_fields:
            read_fields = ['id']
        records = self.create(vals_list)
        return records.read(fields=read_fields)

    def write_and_read(self, vals, read_fields=None):
        if not read_fields:
            read_fields = ['id']
        self.write(vals)
        return self.read(fields=read_fields)
