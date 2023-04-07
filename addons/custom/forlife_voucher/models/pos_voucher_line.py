from odoo import api, fields, models


class PosVoucherLine(models.Model):
    _name = 'pos.voucher.line'
    _description = 'Voucher used by Pos Order'

    pos_order_id = fields.Many2one('pos.order')
    voucher_id = fields.Many2one('voucher.voucher')
    priority = fields.Integer('Ưu tiên')
    voucher_code = fields.Char(string='Mã voucher', related='voucher_id.name')
    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True, related='voucher_id.type')
    end_date = fields.Datetime('Ngày hết hạn', related='voucher_id.end_date')
    price_used = fields.Monetary('Giá trị đã dùng')
    price_residual = fields.Monetary('Giá trị còn lại', related='voucher_id.price_residual')
    price_residual_no_compute = fields.Monetary('Giá trị còn lại ')
    voucher_name = fields.Char('Tên')
    currency_id = fields.Many2one('res.currency', related='voucher_id.currency_id')
    brand_id = fields.Many2one('res.brand')
    partner = fields.Many2one('res.partner')
    store_ids = fields.Many2many('store')
    state = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string='State', required=True,
                             tracking=True, default='new')
    start_date = fields.Datetime('Start date')
    apply_contemp_time = fields.Boolean()
    payment_method_id = fields.Many2one('pos.payment.method')
    price_change = fields.Monetary()
    using_limit = fields.Integer('Giới hạn sử dụng')

