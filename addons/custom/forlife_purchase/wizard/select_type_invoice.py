from odoo import fields, models, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError

class SelectTypeInvoice(models.TransientModel):
    _name = "select.type.invoice"
    _description = "Select Type Invoice"

    select_type_inv = fields.Selection(string="Loại hóa đơn", required=True,
        selection=[
            ('expense', 'Hóa đơn chi phí mua hàng'),
            ('labor', 'Hóa đơn chi phí nhân công'),
            ('normal', 'Hóa đơn chi tiết hàng hóa'),
        ], default='normal')
    partner_id = fields.Many2one('res.partner', string='Đối tác')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ')
    exchange_rate = fields.Float(string='Tỷ giá', default=1)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.currency_id = self.env.company.currency_id if not self.partner_id.property_purchase_currency_id else self.partner_id.property_purchase_currency_id

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        self.exchange_rate = self.currency_id.inverse_rate or 1

    def select_type_invoice(self):
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        purchase_ids = self.env['purchase.order'].search([('id', 'in', active_ids)])

        if any(x.custom_state != 'approved' for x in purchase_ids):
            raise UserError(_('Tất cả Đơn mua hàng phải ở trạng thái Phê duyệt, vui lòng kiểm tra lại!'))

        if len(purchase_ids) == 1:
            purchase_ids.write({
                'select_type_inv': self.select_type_inv,
            })
            if self.select_type_inv in ['expense', 'labor']:
                moves = purchase_ids.action_create_invoice(self.partner_id, self.currency_id, self.exchange_rate)
            else:
                moves = purchase_ids.action_create_invoice()
            if not moves:
                raise UserError(_('Tất cả sản phẩm đã được lên hóa đơn đầy đủ, vui lòng kiểm tra lại!'))
            return {
                'name': 'Hóa đơn nhà cung cấp',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_id': False,
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves.ids)],
            }
        else:
            if len(purchase_ids.mapped('partner_id')) > 1:
                raise UserError(_('Vui lòng chọn các PO có cùng Nhà cung cấp!'))
            if len(purchase_ids.mapped('currency_id')) > 1:
                raise UserError(_('Vui lòng chọn các PO có cùng Đơn vị tiền tệ!'))
            if len(set(purchase_ids.mapped('exchange_rate'))) > 1:
                raise UserError(_('Vui lòng chọn các PO có cùng Tỷ giá tiền tệ!'))
            if len(purchase_ids.mapped('company_id')) > 1:
                raise UserError(_('Vui lòng chọn các PO có cùng Công ty!'))
            if len(set(purchase_ids.mapped('purchase_type'))) > 1:
                raise UserError(_('Vui lòng chọn các PO có cùng Loại mua hàng!'))

            purchase_ids.write({
                'select_type_inv': self.select_type_inv,
            })

            if self.select_type_inv in ['expense', 'labor']:
                moves = purchase_ids.create_invoice_multiple_purchase_orders(self.select_type_inv, self.partner_id, self.currency_id, self.exchange_rate)
            else:
                moves = purchase_ids.create_invoice_multiple_purchase_orders(select_type_inv=self.select_type_inv)

            if not moves:
                raise UserError(_('Tất cả sản phẩm đã được lên hóa đơn đầy đủ, vui lòng kiểm tra lại!'))
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

