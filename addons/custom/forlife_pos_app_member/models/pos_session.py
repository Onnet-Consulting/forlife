# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        loaded_data['default_partner_group'] = self.env.ref('forlife_pos_app_member.partner_group_c').read(['name'])[0]
        default_partner_retail_type = self.env['res.partner.retail'].search(
            [('brand_id', '=', self.config_id.store_id.brand_id.id), ('retail_type', '=', 'customer')],
            limit=1
        )
        loaded_data['default_partner_retail_type_id'] = default_partner_retail_type.id if default_partner_retail_type else False

    def _loader_params_res_partner(self):
        res = super()._loader_params_res_partner()
        domain = res['search_params']['domain']
        domain = expression.AND([domain, [('group_id', '=', self.env.ref('forlife_pos_app_member.partner_group_c').id)]])
        res['search_params']['domain'] = domain
        res['search_params']['fields'].extend(['birthday', 'gender'])
        return res
