from odoo import fields, models, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError

class SelectTypeInvoice(models.TransientModel):
    _name = "select.type.invoice"
    _description = "Select Type Invoice"

    select_type_inv = fields.Selection(
        copy=False,
        default='normal',
        string="Loại hóa đơn",
        required=True,
        selection=[('expense', 'Hóa đơn chi phí mua hàng'),
                   ('labor', 'Hóa đơn chi phí nhân công'),
                   ('normal', 'Hóa đơn chi tiết hàng hóa'),
                   ])

    def select_type_invoice(self):
        req_id = self._context.get('active_ids') or self._context.get('active_id')
        current_purchase = self.env['purchase.order'].search([('id', 'in', req_id)])
        for rec in self:
            if len(current_purchase) == 1:
                for item in current_purchase:
                    if item.purchase_type == 'product' and rec.select_type_inv == 'service':
                        raise UserError(
                            _('Không thể tạo %s với loại mua hàng là %s') %
                            (dict(self._fields['select_type_inv'].selection).get(rec.select_type_inv),
                            dict(item._fields['purchase_type'].selection).get(item.purchase_type)))
                    item.write({
                        'select_type_inv': rec.select_type_inv,
                    })
                moves = current_purchase.action_create_invoice()
                return {
                    'name': 'Hóa đơn nhà cung cấp',
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_id': False,
                    'view_mode': 'tree,form',
                    'domain': [('move_type', '=', 'in_invoice'), ('id', 'in', moves.ids)],
                }
            else:
                has_invalid_item = False
                for item in current_purchase:
                    if item.purchase_type == 'product' and rec.select_type_inv == 'service':
                        has_invalid_item = True
                        break
                    if (item.purchase_type == 'service' or item.purchase_type == 'asset') and rec.select_type_inv != 'service':
                        has_invalid_item = True
                        break
                for item in current_purchase:
                    if has_invalid_item:
                        raise UserError(
                            _('Không thể tạo %s với loại mua hàng là %s') %
                           (dict(self._fields['select_type_inv'].selection).get(rec.select_type_inv),
                            dict(item._fields['purchase_type'].selection).get(item.purchase_type)))
                    item.write({
                        'select_type_inv': rec.select_type_inv,
                    })
                moves = current_purchase.create_multi_invoice_vendor()
                return {
                    'name': 'Hóa đơn nhà cung cấp',
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_id': False,
                    'view_mode': 'tree,form',
                    'domain': [('move_type', '=', 'in_invoice'), ('id', 'in', moves.ids)],
                }


    def cancel(self):
        pass

