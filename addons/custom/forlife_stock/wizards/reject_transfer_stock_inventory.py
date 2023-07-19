from odoo import fields, models, api
from datetime import date


class RejectTransferStockInventory(models.TransientModel):
    _name = "reject.transfer.stock.inventory"
    _description = "Reject Transfer"

    rejection_reason = fields.Text()
    cancel_reason = fields.Text()
    type_button_reject = fields.Boolean()

    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['type_button_reject'] = True if self._context.get('click_button') and self._context.get('click_button') == 'reject' else False
        return res

    def action_reject_transfer_stock_inventory(self):
        req_id = self._context.get('active_id')
        content_button = self._context.get('click_button')
        current_request = self.env['transfer.stock.inventory'].search([('id', '=', req_id)], limit=1)
        if current_request:
            if content_button == 'reject':
                current_request.write({'state': 'reject', 'reason_reject': self.rejection_reason})
            else:
                current_request.write({'state': 'cancel', 'reason_cancel': self.cancel_reason})
                data_ox_other = self.env['stock.picking'].search([('transfer_stock_inventory_id', '=', current_request.id), '|', ('other_import', '=', True), ('other_export', '=', True)])
                for item in data_ox_other:
                    if item:
                        item.write({
                            'state': 'cancel'
                        })

            return {
                'name': ('transfer.stock.inventory'),
                'view_mode': 'form',
                'view_id': self.env.ref('forlife_stock.transfer_stock_inventory_from_view').id,
                'res_model': 'transfer.stock.inventory',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_request.id,
            }

