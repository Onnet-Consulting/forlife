# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_promotion_program_ids(self):
        results = self.env['promotion.program'].search(
            ['|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False)])
        print('================================================================')
        print(results)
        return results
