from odoo import fields, models, api
from odoo.osv import expression
from datetime import datetime, time

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('sku_code')

        return result