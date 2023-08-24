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
        rates = self.currency_id._get_rates(self.env.company, fields.Date.today())
        self.exchange_rate = rates.get(self.currency_id) or 1

    def select_type_invoice(self):
        req_id = self._context.get('active_ids') or self._context.get('active_id')
        current_purchase = self.env['purchase.order'].search([('id', 'in', req_id)])
        for rec in self:
            if len(current_purchase) == 1:
                for item in current_purchase:
                    item.write({
                        'select_type_inv': rec.select_type_inv,
                    })
                if rec.select_type_inv in ['expense', 'labor']:
                    moves = current_purchase.action_create_invoice(rec.partner_id, rec.currency_id, rec.exchange_rate)
                else:
                    moves = current_purchase.action_create_invoice()
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
                for item in current_purchase:
                    exit_partner_id = current_purchase.filtered(lambda r: r.partner_id != item.partner_id)
                    if exit_partner_id:
                        raise UserError(_('Khổng thể tạo hóa đơn từ nhiều phiếu PO khác nhà cung cấp!'))
                    item.write({
                        'select_type_inv': rec.select_type_inv,
                    })
                moves = current_purchase.create_multi_invoice_vendor()
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

