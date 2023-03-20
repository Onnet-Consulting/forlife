from odoo import fields, models, api


class RejectPurchaseOrder(models.TransientModel):
    _name = "reject.purchase.order"
    _description = "Reject purchase order"

    rejection_reason = fields.Text()

    def reject_confirm_action(self):
        req_id = self._context.get('active_id')
        current_order = self.env['purchase.order'].search([('id', '=', req_id)], limit=1)
        if current_order:
            current_order.state = "reject"
            current_order.rejection_reason = self.rejection_reason
