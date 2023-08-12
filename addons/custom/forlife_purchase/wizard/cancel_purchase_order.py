from odoo import fields, models, api


class CancelPurchaseOrder(models.TransientModel):
    _name = "cancel.purchase.order"
    _description = "Cancel purchase order"

    cancel_reason = fields.Text(string='Lý do hủy', required=True)

    def cancel_confirm_action(self):
        req_id = self._context.get('active_id')
        current_order = self.env['purchase.order'].search([('id', '=', req_id)], limit=1)
        if current_order:
            current_order.write({
                'custom_state': 'cancel',
                'state': 'cancel',
                'cancel_reason': self.cancel_reason,
            })
            return {
                'name': ('Đơn mua hàng') if not current_order.is_inter_company else ('Đơn mua hàng liên công ty'),
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_order.id,
            }
