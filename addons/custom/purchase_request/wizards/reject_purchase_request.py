from odoo import fields, models, api
from datetime import date


class RejectPurchaseRequest(models.TransientModel):
    _name = "reject.purchase.request"
    _description = "Reject purchase request"

    rejection_reason = fields.Text()

    def reject_confirm_action_purchase_request(self):
        req_id = self._context.get('active_id')
        current_request = self.env['purchase.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'state': 'reject',
                'rejection_reason': self.rejection_reason
            })
            current_request.write({
                'approval_logs_ids': [(0, 0, {
                    'res_model': 'purchase.request',
                    'request_approved_date': date.today(),
                    'approval_user_id': self.env.user.id,
                    'note': 'Reject',
                    'state': 'reject',
                })],
            })
            return {
                'name': ('purchase.request.from'),
                'view_mode': 'form',
                'view_id': self.env.ref('purchase_request.purchase_request_from_view').id,
                'res_model': 'purchase.request',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_request.id,
            }

