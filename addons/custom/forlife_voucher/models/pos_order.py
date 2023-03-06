from unittest.case import _id

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_view_voucher(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_voucher.forlife_voucher_action')
        action['domain'] = [('order_pos', '=', self.id)]
        return action

    def _create_order_picking(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})
        res = super(PosOrder, self.with_context(ctx))._create_order_picking()
        return res
