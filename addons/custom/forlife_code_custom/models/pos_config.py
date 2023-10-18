# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_id = fields.Char('pos_id', compute='_compute_pos_id', store=True)

    @api.depends('store_id', 'store_id.pos_config_ids')
    def _compute_pos_id(self):
        for rec in self:
            pos_id = 0
            if rec.store_id:
                pos_ids = rec.store_id.pos_config_ids.ids
                pos_ids.sort()
                pos_id = pos_ids.index(rec.id) if rec.id and rec.id in pos_ids else len(pos_ids)
            rec.pos_id = '0'+str(pos_id) if pos_id < 10 else str(pos_id)
