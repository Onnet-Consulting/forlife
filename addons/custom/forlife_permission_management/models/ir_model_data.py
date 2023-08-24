# -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def update_to_noupdate(self, data_list):
        search_vals = set()
        for data in data_list:
            module, name = data.split('.', 1)
            if module and name:
                search_vals.add((module, name))
        for val in search_vals:
            ir_data = self.search([('module', '=', val[0]), ('name', '=', val[1])])
            if ir_data:
                ir_data.noupdate = True
