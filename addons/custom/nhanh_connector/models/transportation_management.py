from odoo import fields, api, models
from datetime import datetime
from odoo.exceptions import ValidationError


class TransportationSession(models.Model):
    _name = 'transportation.session'
    _description = 'Phiên giao vận'

    name = fields.Char(compute='compute_name', store=1)
    stock_id = fields.Many2one('stock.location', string='Tên kho')
    stock_code = fields.Char(related='stock_id.code', string='Mã kho')
    location_id = fields.Many2one('stock.location', string='Địa điểm')
    date = fields.Datetime(string='Ngày thực hiện', default=datetime.today())
    user_id = fields.Many2one('res.users', string='Người thực hiện', default=lambda self: self.env.user)
    type = fields.Selection([('in', 'Nhập kho'), ('out', 'Xuất kho')], string='Loại giao vận')
    order_count = fields.Integer(string='Tổng số đơn', compute='compute_count')
    session_line = fields.One2many('transportation.session.line', 'session_id', string='Đơn hàng')
    status = fields.Selection([('draft', 'Dự thảo'), ('done', 'Hoàn thành')], string='Trạng thái', default='draft')

    @api.depends('session_line')
    def compute_count(self):
        for rec in self:
            rec.order_count = len(rec.session_line)

    @api.depends('user_id')
    def compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.user_id.name, datetime.today().strftime('%d/%m/%Y'))

    def action_done(self):
        orders = self.session_line
        for order in orders:
            pickings = order.order_id.picking_ids
            if not pickings:
                order.status = 'order_404'
            for picking in pickings:
                if picking.state in ('done', 'cancel'):
                    continue
                try:
                    picking.action_set_quantities_to_reservation()
                    picking = picking.with_context(skip_immediate=True).button_validate()
                    order.update_state(is_done=picking)
                except Exception:
                    picking = picking
                    order.update_state(picking=picking, is_done=False)

        self.status = 'done'

    def unlink(self):
        if self.status == 'done':
            raise ValidationError('Không thể xóa phiên đã hoàn thành!.')
        return super().unlink()


class TransportationSessionLine(models.Model):
    _name = 'transportation.session.line'
    _description = 'Chi tiết phiên giao vận'

    session_id = fields.Many2one('transportation.session', string='Phiên')
    order_id = fields.Many2one('sale.order', string='Mã đơn hàng odoo')
    nhanh_id = fields.Char(string='Mã đơn hàng NhanhVN')
    delivery_carrier_id = fields.Many2one(related='order_id.delivery_carrier_id', string='Đơn vị vận chuyển')
    order_line = fields.One2many(related='order_id.order_line', string='Số SP')
    nhanh_status = fields.Selection(related='order_id.nhanh_order_status', string='Trạng thái NhanhVN')
    order_status = fields.Selection(related='order_id.state', string='Trạng thái đơn hàng')
    channel = fields.Many2one(related='order_id.sale_channel_id', string='Kênh/Sàn')
    transport_code = fields.Char(related='order_id.x_transfer_code', string='Mã đơn vận')
    status = fields.Selection([
        ('out_success', 'Xuất kho thành công'),
        ('in_success', 'Nhập kho thành công'),
        ('no_picking', 'Chưa tạo phiếu kho'),
        ('not_enough', 'Không đủ tồn'),
        ('error', 'Không thành công'),
        ('order_404', 'Không có đơn hàng'),
    ], string='Trạng thái')

    def update_state(self, is_done, picking=None):
        if is_done and self.session_id.type == 'in':
            self.status = 'in_success'
        if is_done and self.session_id.type == 'out':
            self.status = 'out_success'
        if not is_done:
            self.status = self.check_picking(picking)

    def check_picking(self, picking):
        if picking.state == 'confirmed':
            return 'not_enough'
        if picking.state == 'waiting':
            return 'error'
