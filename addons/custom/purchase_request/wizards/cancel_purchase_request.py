from odoo import fields, models, api


class CancelPurchaseRequest(models.TransientModel):
    _name = "cancel.purchase.request"
    _description = "Cancel purchase request"

    def create_purchase_request_draft(self):
        req_id = self._context.get('active_id')
        current_request = self.env['purchase.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'state': 'cancel',
            })
            return {
                'name': ('purchase.request.from'),
                'view_mode': 'form',
                'view_id': self.env.ref('purchase_request.purchase_request_from_view').id,
                'res_model': 'purchase.request',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }

    def action_cancel(self):
        req_id = self._context.get('active_id')
        current_request = self.env['purchase.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'state': 'cancel',
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

