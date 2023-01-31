from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        res = super(PosSession, self)._loader_params_res_partner()
        data = res['search_params']['fields']
        data.append('total_points_available_forlife')
        data.append('total_points_available_format')
        res['search_params']['fields'] = data
        return res