from odoo import fields, models, api
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_starting_sequence(self):
        res = super(AccountMove, self)._get_starting_sequence()
        res += '-'+str(datetime.now().timestamp())
        return res