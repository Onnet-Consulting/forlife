from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class PosLaundry (models.Model):
    _name = 'pos.laundry'
    _description = 'Nghiệp vụ giặt là'
    _inherit = ['mail.thread']

    name = fields.Char(string='Số phiếu', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('pos.laundry.sequence'))
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', related='company_id.currency_id')
    customer_id = fields.Many2one('res.partner', string='Khách hàng', required=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    department_id = fields.Many2one('hr.department', string='Bộ phận sửa chữa', required=True)
    store_id = fields.Many2one('store', string='Chi nhánh', required=True)
    date = fields.Datetime(string='Ngày nhận', required=True)
    due_date = fields.Datetime(string='Ngày hẹn trả', required=True)
    amount_total = fields.Monetary(string='Tổng cộng', currency_field='currency_id', compute='compute_amount_total', store=True)
    voucher = fields.Char(string='Mã voucher')
    first_value = fields.Monetary(string='Giá trị ban đầu', currency_field='currency_id', compute='compute_first_value', store=True)
    reject_value = fields.Monetary(string='Giá trị từ chối', currency_field='currency_id',  compute='compute_reject_value', store=True)
    approved_value = fields.Monetary(string='Giá trị sử dụng', currency_field='currency_id', compute='compute_approved_value', store=True)
    type = fields.Selection([('laundry', 'Giặt là'), ('repair', 'Sửa đồ')], string='Loại phiếu', required=True)
    description = fields.Text(string='Diễn giải')
    lines = fields.One2many('pos.laundry.line', 'laundry_id', string='Chi tiết dịch vụ')
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('in-process', 'Đang thực hiện'),
        ('reject', 'Từ chối'),
        ('done', 'Hoàn thành')
    ], string='Trạng thái', default='draft')

    @api.onchange('voucher')
    def onchange_voucher(self):
        if self.voucher:
            voucher = self.action_check_voucher()
            self.approved_voucher(voucher)

    @api.depends('voucher', 'amount_total', 'lines.repair_status_id')
    def compute_first_value(self):
        for rec in self:
            if not rec.voucher:
                return
            rec.first_value = 0
            voucher = self.env['voucher.voucher'].search([('name', '=', rec.voucher)], limit=1)
            if voucher.price_residual == rec.amount_total:
                rec.first_value = rec.amount_total
            elif voucher.price_residual < rec.amount_total:
                rec.first_value = voucher.price_residual

    @api.depends('lines.amount', 'lines.repair_status_id', 'first_value')
    def compute_approved_value(self):
        for rec in self:
            rec.approved_value = rec.first_value
            if rec.first_value > 0:
                reject_value = rec.lines.filtered(lambda x: x.repair_status_id.refund)
                rec.approved_value = rec.first_value - sum(reject_value.mapped('amount'))

    @api.depends('lines.amount', 'lines.repair_status_id')
    def compute_amount_total(self):
        for rec in self:
            approved = rec.lines.filtered(lambda x: not x.repair_status_id.refund)
            rec.amount_total = sum(approved.mapped('amount'))

    @api.depends('lines.repair_status_id', 'lines.amount')
    def compute_reject_value(self):
        for rec in self:
            reject = rec.lines.filtered(lambda x: x.repair_status_id.refund)
            rec.reject_value = sum(reject.mapped('amount'))

    def action_check_voucher(self):
        error = ''
        voucher = self.env['voucher.voucher'].search([('name', '=', self.voucher)], limit=1)
        if not voucher:
            error += 'Mã voucher không hợp lệ. Vui lòng kiểm tra lại! \n'
        if voucher and not voucher.purpose_id.is_gift:
            error += 'Mã voucher không dùng cho dịch vụ này. Vui lòng kiểm tra lại!. \n'
        if voucher and voucher.state not in ('sold', 'valid'):
            error += 'Mã voucher chưa được đủ điều kiện áp dụng. Vui lòng kiểm tra lại! \n'
        if voucher and self.date < voucher.start_date and self.date > voucher.end_date:
            error += 'Mã voucher nằm ngoài thời gian áp dụng. Vui lòng kiểm tra lại! \n'
        if voucher and voucher.price_residual <= 0:
            error += 'Mã voucher đã sử dụng hết giá trị. Vui lòng kiểm tra lại! \n'
        if voucher and voucher.state_app:
            error += 'Mã voucher chưa được kích hoạt. Vui lòng kiểm tra lại! \n'
        if error:
            self.voucher = False
            raise ValidationError(error)
        return voucher

    def approved_voucher(self, voucher):
        val = {
            'price_used': voucher.price_used + self.first_value,
            'price_residual': voucher.price_residual - self.first_value,
        }
        if val['price_residual'] > 0 and voucher.state == 'sold':
            val['state'] = 'valid'
        elif val['price_residual'] <= 0:
            val['state'] = 'off value'
        elif val['price_residual'] > 0 and voucher.state == 'valid':
            pass
        voucher.update(val)

    def approved_reject_value(self, voucher):
        voucher = self.env['voucher.voucher'].search([('name', '=', voucher)], limit=1)
        val = {
            'price_used': voucher.price_used - self.first_value,
            'price_residual': voucher.price_residual + self.first_value,
        }
        if voucher.state == 'off value':
            val['state'] = 'valid'
        voucher.write(val)

    def approve(self):
        voucher = self.action_check_voucher()
        self.approved_voucher(voucher)
        self.state = 'in-process'


class PosLaundryLine(models.Model):
    _name = 'pos.laundry.line'
    _description = 'Chi tiết'

    laundry_id = fields.Many2one('pos.laundry', string='Mã phiếu')
    company_id = fields.Many2one('res.company', related='laundry_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    product_name = fields.Char(string='Sản phẩm', required=True)
    status_id = fields.Many2one('laundry.product.status', string='Tình trạng', required=True)
    service_id = fields.Many2one('laundry.service', string='Dịch vụ', required=True)
    request_note = fields.Char(string='Yêu cầu')
    amount = fields.Monetary(string='Chi phí', currency_field='currency_id', compute='compute_amount', store=True)
    first_amount = fields.Monetary(string='Chi phí ban đầu', currency_field='currency_id', compute='compute_amount', store=True)
    send_date = fields.Datetime(string='Ngày hàng đi')
    receive_date = fields.Datetime(string='Ngày hàng về')
    repair_status_id = fields.Many2one('laundry.repair.status', string='Tình trạng sửa chữa', required=True)
    repair_status_refund = fields.Boolean(related='repair_status_id.refund')
    delivery_date = fields.Datetime(string='Ngày giao hàng')
    note = fields.Text(string='Ghi chú')

    @api.depends('service_id', 'laundry_id.voucher')
    def compute_amount(self):
        for rec in self:
            rec.first_amount = rec.service_id.amount
            if rec.laundry_id.voucher:
                voucher = self.env['voucher.voucher'].search([('name', '=', rec.laundry_id.voucher)], limit=1)
                rec.amount = rec.first_amount - voucher.price_residual

    def write(self, vals):
        if 'repair_status_id' in vals:
            self.laundry_id.message_post_with_view(
                'forlife_point_of_sale.mail_message_change_repair_status_id',
                values={'from': self.repair_status_id.name, 'to': self.repair_status_id.browse(int(vals['repair_status_id'])).name},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        res = super().write(vals)
        if res and self.laundry_id.voucher:
            self.laundry_id.approved_reject_value(self.laundry_id.voucher)
        return res

