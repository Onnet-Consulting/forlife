from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        if 'invoice_line_ids' in vals_list:
            for line in vals_list['invoice_line_ids']:
                if line[0] == 0:
                    if line[2].get('qty_returned'):
                        line[2]['quantity'] = line[2].get('quantity') - line[2].pop('qty_returned')
        return super(AccountMove, self).create(vals_list)