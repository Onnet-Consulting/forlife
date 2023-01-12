# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ResCompany, self.with_context(from_create_company=True)).create(vals_list)
        return res
