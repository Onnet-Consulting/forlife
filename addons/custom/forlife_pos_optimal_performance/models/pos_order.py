from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        context = self.env.context
        if not context.get('job_uuid', False):
            return super(PosOrder, self).with_delay(channel='pos_process_payment')._process_payment_lines(pos_order, order, pos_session, draft)
        return super(PosOrder, self)._process_payment_lines(pos_order, order, pos_session, draft)

    def _create_order_picking(self):
        context = self.env.context
        if not context.get('job_uuid', False):
            return super(PosOrder, self).with_delay(channel='pos_order_picking')._create_order_picking()
        return super(PosOrder, self)._create_order_picking()