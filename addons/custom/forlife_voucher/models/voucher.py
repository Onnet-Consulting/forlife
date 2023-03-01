from odoo import api, fields, models
import phonenumbers
from odoo.addons.forlife_pos_app_member.models.res_utility import get_valid_phone_number, is_valid_phone_number
import string
import random
from datetime import datetime


class Voucher(models.Model):
    _name = 'voucher.voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Voucher'

    name = fields.Char('Code', compute='_compute_name', store=True)
    program_voucher_id = fields.Many2one('program.voucher', 'Program name')
    purpose_id = fields.Many2one('setup.voucher', 'Purpose', required=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_field')  # related currency of program voucher
    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True)
    state = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string='State', required=True, tracking=True, default='new')
    price = fields.Monetary('Mệnh giá')
    price_used = fields.Monetary('Giá trị đã dùng')
    price_residual = fields.Monetary('Giá trị còn lại')
    start_date = fields.Datetime('Start date')
    end_date = fields.Datetime('End date', tracking=True)
    apply_many_times = fields.Boolean('Apply many times')

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời')

    purchase_id = fields.Many2one('purchase.order', 'Đơn hàng mua')

    state_app = fields.Boolean('Trạng thái App', tracking=True)

    status_latest = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string="Latest status")

    sale_id = fields.Many2one('sale.order', 'Đơn hàng bán')

    order_pos = fields.Many2one('pos.order', 'Đơn hàng POS')

    order_use_ids = fields.Many2many('pos.order', string='Đơn hàng sử dụng')

    partner_id = fields.Many2one('res.partner')
    phone_number = fields.Char(copy=False, string='Phone')

    product_voucher_id = fields.Many2one('product.template', 'Product Voucher')

    derpartment_id = fields.Many2one('hr.department', 'Department Code', required=True)
    brand_id = fields.Many2one('res.brand', 'Brand', required=True)
    store_ids = fields.Many2many('store', string='Cửa hàng áp dụng')

    @api.depends('program_voucher_id')
    def _compute_currency_field(self):
        for rec in self:
            rec.currency_id = rec.program_voucher_id.currency_id

    @api.depends('program_voucher_id')
    def _compute_name(self):
        for v in self:
            if v.program_voucher_id:
                X = "V" if v.program_voucher_id.type == 'v' else "E"
                Y = v.program_voucher_id.purpose_id.ref
                T = 1 if v.program_voucher_id.apply_many_times else 0
                Z = 1 if v.program_voucher_id.brand_id.id == self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id else 2
                ABBB = v.program_voucher_id.program_voucher_code
                NNNNN = self._generator_charnumber_code(size=5)
                v.name = '{}{}{}{}{}{}'.format(X, Y, T, Z, ABBB, NNNNN)
            else:
                v.name = ''

    def _generator_charnumber_code(self, size, chars=string.ascii_uppercase + string.digits):
        string_generate = chars.replace("O", "")
        return ''.join(random.choice(string_generate) for _ in range(size))

    @api.onchange('phone_number')
    def onchage_phone_number(self):
        for rec in self:
            partner_phone = self.env['res.partner'].search([('phone', '=', rec.phone_number)], limit=1)
            partner_mobile = self.env['res.partner'].search([('mobile', '=', rec.phone_number)], limit=1)
            if partner_phone or partner_mobile:
                rec.partner_id = partner_phone.id or partner_mobile.id
            else:
                rec.partner_id = False

    @api.constrains('phone_number')
    def _check_phone(self):
        for rec in self:
            if rec.phone_number and not is_valid_phone_number(rec.phone_number):
                raise ValidationError(_('Invalid phone number - %s') % rec.phone_number)

    def check_due_date_voucher(self):
        now = datetime.now()
        vouchers = self.search([('state', '!=', 'expired')])
        if vouchers:
            for rec in vouchers:
                if rec.end_date and rec.end_date < now:
                    rec.state = 'expired'

    def write(self, values):
        for record in self:
            old_state = record.state
            if 'state' in values and values['state']:
                values['status_latest'] = old_state
        return super(Voucher, self).write(values)
