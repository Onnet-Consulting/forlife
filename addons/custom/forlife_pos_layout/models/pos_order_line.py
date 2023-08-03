from odoo import fields, api, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _order_line_fields(self, line, session_id=None):
        res = super()._order_line_fields(line=line, session_id=session_id)
        if line and 'discount_cash_amount' in line[2] and line[2]['discount_cash_amount'] > 0:
            res[2]['discount_cash_amount'] = line[2]['discount_cash_amount']
        return res
