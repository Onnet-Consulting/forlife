from odoo import fields, models, api, _

class SelectTypeInvoice(models.TransientModel):
    _inherit = "select.type.invoice"
    _description = "Select Type Invoice"

    def select_type_invoice(self):
        req_id = self._context.get('active_ids') or self._context.get('active_id')
        current_purchase = self.env['purchase.order'].search([('id', 'in', req_id)])
        if len(current_purchase) == 1 and current_purchase.is_return:
            moves = current_purchase.action_create_invoice()
            return {
                'name': 'Hóa đơn trả lại hàng mua',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_id': False,
                'view_mode': 'tree,form',
                'domain': [('move_type', '=', 'in_refund'), ('id', 'in', moves.ids)],
            }
        else:
            return super(SelectTypeInvoice, self).select_type_invoice()