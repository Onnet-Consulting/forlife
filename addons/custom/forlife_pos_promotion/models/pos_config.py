# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_promotion_program_ids(self):
        return self.env['promotion.program'].search(
            [('state', '=', 'in_progress'), '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False)])
