from odoo import fields, models, api


class RejectPurchaseRequest(models.TransientModel):
    _name = "reject.purchase.request"
    _description = "Reject purchase request"

    rejection_reason = fields.Text()

    def reject_confirm_action(self):
        req_id = self._context.get('active_id')
        current_request = self.env['purchase.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.state = "reject"
            current_request.rejection_reason = self.rejection_reason
