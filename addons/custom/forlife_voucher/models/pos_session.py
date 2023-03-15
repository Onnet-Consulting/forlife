from odoo import api, fields, models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
        res = super(PosSession, self)._loader_params_pos_payment_method()
        data = res['search_params']['fields']
        data.append('is_voucher')
        res['search_params']['fields'] = data
        return res