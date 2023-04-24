from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

Character = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class ProgramVoucher(models.Model):
    _name = 'program.voucher'
    _description = 'Program Voucher for Forlife'

    name = fields.Char('Program Voucher Name', required=True)

    program_voucher_code = fields.Char('Voucher Program Code', store=True, copy=False, readonly=True, default='New')

    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True)

    purpose_id = fields.Many2one('setup.voucher', 'Purpose', required=True)

    derpartment_id = fields.Many2one('hr.department', 'Department Code', required=True)

    apply_many_times = fields.Boolean('Apply many times', default=False)

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời')

    brand_id = fields.Many2one('res.brand', 'Brand', required=True)

    start_date = fields.Datetime('Start date', required=True)

    end_date = fields.Datetime('End date', required=True, tracking=True)

    state_app = fields.Boolean('Trạng thái App')

    store_ids = fields.Many2many('store', string='Apply for store')

    product_id = fields.Many2one('product.template', 'Product Voucher', compute='compute_product', inverse='product_inverse', domain=[('voucher','=',True)])

    product_apply_ids = fields.Many2many('product.product', string='Sản phẩm áp dụng')

    product_ids = fields.One2many('product.template', 'program_voucher_id')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    is_full_price_applies = fields.Boolean('Áp dụng nguyên giá')

    using_limit = fields.Integer('Giới hạn sử dụng', default=0)

    details = fields.Char('Diễn giải')

    @api.depends('product_ids')
    def compute_product(self):
        for rec in self:
            if len(rec.product_ids) > 0:
                rec.product_id = rec.product_ids[0]

    def product_inverse(self):
        if len(self.product_ids) > 0:
            product = self.env['product.template'].browse(self.product_ids[0].id)
            product.program_voucher_id = False
        self.product_id.program_voucher_id = self

    program_voucher_line_ids = fields.One2many('program.voucher.line', 'program_voucher_id', string='Voucher', copy=True)

    voucher_ids = fields.One2many('voucher.voucher', 'program_voucher_id')
    voucher_count = fields.Integer('Voucher Count', compute='_compute_count_voucher', store=True)

    @api.constrains('start_date','end_date')
    def check_contrains_date(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise UserError(_('Ngày kết thúc không được nhỏ hơn ngày bắt đầu! '))

    @api.onchange('type')
    def onchange_type_program_voucher(self):
        if self.type == 'v':
            self.apply_many_times = False

    @api.depends('voucher_ids')
    def _compute_count_voucher(self):
        for rec in self:
            if rec.voucher_ids:
                rec.voucher_count = len(rec.voucher_ids)
            else:
                rec.voucher_count = 0

    def change_prefix_sequence(self, code: str):
        for i in range(len(Character)):
            if code == Character[i]:
                return Character[i + 1]

    @api.model
    def create(self, vals):
        last_record = self.get_last_sequence()
        if last_record:
            #change character of sequence
            code = last_record.program_voucher_code
            if code[1:] == '999':
                seq = self.env['ir.sequence'].search([('code', '=', 'program.voucher')])
                vals_seq = {
                    'prefix': self.change_prefix_sequence(code[0]),
                    'number_next_actual': 1,

                }
                seq.write(vals_seq)
        if vals.get('program_voucher_code', 'New') == 'New':
            vals['program_voucher_code'] = self.env['ir.sequence'].next_by_code('program.voucher') or 'New'
        return super(ProgramVoucher, self).create(vals)

    def get_last_sequence(self):
        last_record = self.env['program.voucher'].search([], limit=1, order='id desc')
        if last_record:
            return last_record
        return False

    def create_voucher(self):
        if len(self.program_voucher_line_ids) > 0:
            for rec in self.program_voucher_line_ids:
                if rec.partner_ids:
                    for p in rec.partner_ids:
                        for i in range(rec.count):
                            self.env['voucher.voucher'].create({
                                'program_voucher_id': self.id,
                                'start_date':self.start_date,
                                'state':'new',
                                'partner_id': p.id,
                                'price': rec.price,
                                'price_used': 0,
                                'price_residual': rec.price - 0,
                                'end_date':self.end_date,
                            })
                    self.program_voucher_line_ids = [(5, self.program_voucher_line_ids.ids)]
                if not rec.partner_ids:
                    for i in range(rec.count):
                        self.env['voucher.voucher'].create({
                            'program_voucher_id': self.id,
                            'start_date': self.start_date,
                            'state': 'new',
                            'price': rec.price,
                            'price_used': 0,
                            'price_residual': rec.price - 0,
                            'end_date': self.end_date,
                        })
                    self.program_voucher_line_ids = [(5, self.program_voucher_line_ids.ids)]
        else:
            raise UserError(_("Vui lòng thêm dòng thông tin cho vourcher!"))

    def action_view_voucher_relation(self):
        self.ensure_one()
        return {
            'name': _('Voucher'),
            'domain': [('id', 'in', self.voucher_ids.ids)],
            'res_model': 'voucher.voucher',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }

    def unlink(self):
        for rec in self:
            if rec.voucher_ids:
                raise ValidationError(_('Bạn không được phép xóa chương trình chứa mã Voucher!'))
        return super(ProgramVoucher, self).unlink()



