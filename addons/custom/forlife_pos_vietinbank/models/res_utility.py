from odoo import fields, api, models
import json


class ResUtilityInherit(models.AbstractModel):
    _inherit = 'res.utility'

    @api.model
    def get_statement_inquiry_api(self, pos_id):
        return json.dumps(self.env['apis.vietinbank'].get_statement_inquiry(pos_id))
