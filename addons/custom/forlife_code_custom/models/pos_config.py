# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_id = fields.Integer('pos_id', compute='_compute_pos_id', store=True)

    @api.depends('store_id', 'store_id.pos_config_ids')
    def _compute_pos_id(self):
        for rec in self:
            if rec.store_id:
                pos_ids = rec.store_id.pos_config_ids.ids
                pos_ids.sort()
                rec.pos_id = pos_ids.index(rec.id) if rec.id else len(pos_ids)
            else:
                rec.pos_id = 0