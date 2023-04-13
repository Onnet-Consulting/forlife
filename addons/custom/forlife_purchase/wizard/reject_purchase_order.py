from odoo import fields, models, api


class RejectPurchaseOrder(models.TransientModel):
    _name = "reject.purchase.order"
    _description = "Reject purchase order"

    rejection_reason = fields.Text(string='Lý do từ chối')

    def reject_confirm_action(self):
        req_id = self._context.get('active_id')
        current_order = self.env['purchase.order'].search([('id', '=', req_id)], limit=1)
        if current_order:
            current_order.custom_state = "reject"
            current_order.rejection_reason = self.rejection_reason
            return {
                'name': ('Đơn mua hàng') if not current_order.is_inter_company else ('Đơn mua hàng liên công ty'),
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_order.id,
            }
