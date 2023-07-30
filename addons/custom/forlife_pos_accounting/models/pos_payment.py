from odoo import models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    def _create_payment_moves(self):
        result = super()._create_payment_moves()
        for payment in self:
            order = payment.pos_order_id
            move = payment.account_move_id
            if not order.real_to_invoice and move:
                store_partner = self.session_id.config_id.store_id.contact_id
                to_update_move_lines = move.line_ids.filtered(lambda line: line.partner_id)
                if store_partner and to_update_move_lines:
                    to_update_move_lines.partner_id = store_partner
        return result
