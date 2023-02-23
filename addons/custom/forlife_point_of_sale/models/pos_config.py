# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    store_id = fields.Many2one('store', string='Store', required=True, domain="[('company_id', '=', company_id)]")

    def get_pos_opened(self):
        query = '''SELECT (SELECT name FROM pos_config WHERE id = ps.config_id), ps.start_at FROM pos_session ps WHERE ps.state = 'opened' AND ps.config_id = %s'''
        self.env.cr.execute(query, (self.id,))
        data = self.env.cr.fetchall()

        return data