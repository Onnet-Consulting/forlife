# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    store_id = fields.Many2one('store', string='Store', required=True, domain="[('company_id', '=', company_id)]")

    def action_archive(self):
        for rec in self:
            rec.store_id.action_archive()
        return super().action_archive()

    def action_unarchive(self):
        for rec in self:
            rec.store_id.action_unarchive()
        return super().action_unarchive()
