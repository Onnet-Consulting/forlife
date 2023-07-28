from odoo import fields, api, models
from datetime import datetime
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
import tempfile


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
    re_confirm = fields.Boolean(compute='reconfirm', default=False)
    template_excel = fields.Binary(string='Template', compute='_get_template')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)

    def _get_template(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        # Lấy đường dẫn của file tạm
        temp_file_path = temp_file.name
        workbook = xlsxwriter.Workbook(temp_file_path)
        worksheet = workbook.add_worksheet(u'Sheet0')

        header = ['Mã đơn hàng NhanhVN']
        lines = [header]

        if self.re_confirm:
            data = [[line.nhanh_id] for line in self.session_line.filtered(lambda x: x.select)]
        else:
            data = [[line.nhanh_id] for line in self.session_line]
        lines += data
        header_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': '11',
            'text_wrap': True,
            'italic': False,
            'border': 1,
        })
        row = 0
        for line in lines:
            col = 0
            for item in line:
                if row == 0:
                    worksheet.write(row, col, item, header_format)
                else:
                    worksheet.write(row, col, item)
                col += 1
            row += 1
        worksheet.set_column(0, len(header), 20)
        worksheet.set_row(0, 30)
        workbook.close()
        # Đóng file
        temp_file.close()
        self.template_excel = base64.b64encode(open(temp_file_path, "rb").read())

    @api.depends('session_line.select')
    def reconfirm(self):
        for rec in self:
            if rec.session_line.filtered(lambda x: x.select):
                rec.re_confirm = True
            else:
                rec.re_confirm = False

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
                if picking.state in ('cancel'):
                    continue
                if picking.state in ('done') and self.type == 'in':
                    order.status = 'in_success'
                    continue
                if picking.state in ('done') and self.type == 'out':
                    order.status = 'out_success'
                    continue
                try:
                    picking.action_set_quantities_to_reservation()
                    picking_done = picking.with_context(skip_immediate=True).button_validate()
                    if picking_done == True:
                        order.update_state(is_done=picking)
                    else:
                        order.update_state(picking=picking, is_done=False)
                except Exception:
                    picking = picking
                    order.update_state(picking=picking, is_done=False)
        self.session_line.write({'select': False})
        self.status = 'done'

    def action_export(self):
        export = {
            'type': 'ir.actions.act_url',
            'name': 'Export fee',
            'url': '/web/content/%s/%s/template_excel/danh_sach_don_hang_nhanhvn.xlsx?download=true' % (
                self._name, self.id),
        }
        self.template_excel = False
        self.session_line.write({'select': False})
        return export

    def unlink(self):
        if self.status == 'done':
            raise ValidationError('Không thể xóa phiên đã hoàn thành!.')
        return super().unlink()


class TransportationSessionLine(models.Model):
    _name = 'transportation.session.line'
    _description = 'Chi tiết phiên giao vận'

    session_id = fields.Many2one('transportation.session', string='Phiên')
    picking_id = fields.Char(string='Phiếu kho', compute='compute_picking')
    select = fields.Boolean(string='  ')
    order_id = fields.Many2one('sale.order', string='Mã đơn hàng odoo')
    nhanh_id = fields.Char(string='Mã đơn hàng NhanhVN')
    delivery_carrier_id = fields.Many2one(related='order_id.delivery_carrier_id', string='Đơn vị vận chuyển')
    order_line = fields.One2many(related='order_id.order_line', string='Số SP')
    nhanh_status = fields.Selection(related='order_id.nhanh_order_status', string='Trạng thái NhanhVN')
    order_status = fields.Selection(related='order_id.state', string='Trạng thái đơn hàng')
    channel = fields.Many2one(related='order_id.sale_channel_id', string='Kênh/Sàn')
    transport_code = fields.Char(related='order_id.x_transfer_code', string='Mã vận đơn')
    company_id = fields.Many2one(related='session_id.company_id')
    status = fields.Selection([
        ('out_success', 'Xuất kho thành công'),
        ('in_success', 'Nhập kho thành công'),
        ('no_picking', 'Chưa tạo phiếu kho'),
        ('not_enough', 'Không đủ tồn'),
        ('error', 'Không thành công'),
        ('order_404', 'Không có đơn hàng'),
    ], string='Trạng thái')

    @api.depends('order_id')
    def compute_picking(self):
        for rec in self:
            rec.picking_id = ', '.join(x.name for x in rec.order_id.picking_ids)

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
        if picking.state == 'assigned':
            if picking.move_line_ids_without_package:
                return 'not_enough'
            return 'error'
