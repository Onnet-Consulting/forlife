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

    @api.model
    def loader_data_res_partner_from_ui(self, data):
        partner_update = self.env['res.partner'].sudo().search([('id', '=', data[0])])
        return {
            'total_points_available_forlife': partner_update.total_points_available_forlife,
            'total_points_available_format': partner_update.total_points_available_format
        }
