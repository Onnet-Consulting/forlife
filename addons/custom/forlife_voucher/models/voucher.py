from odoo import api, fields, models, _
import phonenumbers
from odoo.addons.forlife_pos_app_member.models.res_utility import get_valid_phone_number, is_valid_phone_number
import string
import random
from datetime import datetime
from odoo.exceptions import ValidationError
import pytz


class Voucher(models.Model):
    _name = 'voucher.voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Voucher'

    name = fields.Char('Code', compute='_compute_name', store=True, readonly=False)
    program_voucher_id = fields.Many2one('program.voucher', 'Program name')
    purpose_id = fields.Many2one('setup.voucher', 'Purpose', related='program_voucher_id.purpose_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_field')  # related currency of program voucher
    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Loại', related='program_voucher_id.type')
    state = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string='State', required=True,
                             tracking=True, default='new')
    price = fields.Monetary('Mệnh giá')
    price_used = fields.Monetary('Giá trị đã dùng')
    price_residual = fields.Monetary('Giá trị còn lại', compute='_compute_price_residual', store=True)
    start_date = fields.Datetime('Start date')
    end_date = fields.Datetime('End date', tracking=True)
    apply_many_times = fields.Boolean('Apply many times', related='program_voucher_id.apply_many_times')

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời', related='program_voucher_id.apply_contemp_time')

    purchase_id = fields.Many2one('purchase.order', 'Đơn hàng mua')

    state_app = fields.Boolean('Trạng thái App', tracking=True)

    status_latest = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string="Latest status")

    sale_id = fields.Many2one('sale.order', 'Đơn hàng bán')

    order_pos = fields.Many2one('pos.order', 'Đơn hàng POS')

    order_use_ids = fields.Many2many('pos.order', string='Đơn hàng sử dụng')

    partner_id = fields.Many2one('res.partner')
    phone_number = fields.Char(copy=False, string='Phone')

    product_voucher_id = fields.Many2one('product.template', 'Product Voucher', related='program_voucher_id.product_id')
    product_apply_ids = fields.Many2many('product.product', string='Sản phẩm áp dụng', related='program_voucher_id.product_apply_ids')
    derpartment_id = fields.Many2one('hr.department', 'Department Code', related='program_voucher_id.derpartment_id')
    brand_id = fields.Many2one('res.brand', 'Brand', related='program_voucher_id.brand_id')
    store_ids = fields.Many2many('store', string='Cửa hàng áp dụng', related='program_voucher_id.store_ids')
    is_full_price_applies = fields.Boolean('Áp dụng nguyên giá', related='program_voucher_id.is_full_price_applies')
    using_limit = fields.Integer('Giới hạn sử dụng', default=0, related='program_voucher_id.using_limit')

    notification_id = fields.Char('Notification ID', help='Id của thông báo trên trang quản trị app,'
                                                          ' dùng cho nghiệp vụ đẩy thông báo thông tin voucher cho khách hàng.')

    @api.depends('price_used', 'price')
    def _compute_price_residual(self):
        for rec in self:
            rec.price_residual = rec.price - rec.price_used

    def write(self, values):
        if 'lang' not in self._context:
            self._context['lang'] = self.env.user.lang
        now = datetime.now()
        for rec in self:
            if rec.status_latest and 'end_date' in values and values['end_date']:
                end_date = datetime.strptime(values['end_date'], '%Y-%m-%d %H:%M:%S')
                if now < end_date != rec.end_date:
                    values['state'] = rec.status_latest
        return super(Voucher, self).write(values)

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
                if not v.name:
                    v.name = '{}{}{}{}{}{}'.format(X, Y, T, Z, ABBB, NNNNN)
                else:
                    v.name = v.name

    def _generator_charnumber_code(self, size, chars=string.ascii_uppercase + string.digits):
        string_generate = chars.replace("O", "")
        return ''.join(random.choice(string_generate) for _ in range(size))

    @api.onchange('phone_number')
    def onchage_phone_number(self):
        for rec in self:
            partner_phone = self.env['res.partner'].search([('phone', '=', rec.phone_number)], limit=1)
            if partner_phone:
                rec.partner_id = partner_phone.id or partner_mobile.id
            else:
                rec.partner_id = False

    @api.model
    def check_voucher(self, codes):
        data = []
        for code in codes:
            if not code['value']:
                data.append({
                    'value': False,
                })
            else:
                vourcher = self.sudo().search([('name', '=', code['value'])], limit=1)
                if vourcher:
                    # sql = f"SELECT product_product_id FROM product_product_program_voucher_rel WHERE program_voucher_id = {vourcher.program_voucher_id.id}"
                    # self._cr.execute(sql)
                    # product_ids = self._cr.fetchall()
                    # product_ids = [id[0] for id in product_ids]
                    start_date = self._format_time_zone(vourcher.start_date)
                    end_date = self._format_time_zone(vourcher.end_date)
                    end_date_format = datetime.strptime(end_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    minute = end_date_format.minute if end_date_format.minute != 0 else '00'
                    end_date_format = f"{end_date_format.day}/{end_date_format.month}/{end_date_format.year} {end_date_format.hour}:{minute}:{end_date_format.second}"
                    start_date_format = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    data.append({
                        'value': {
                            'voucher_name': vourcher.name,
                            'voucher_id': vourcher.id,
                            'type': vourcher.type,
                            'end_date_not_format': end_date,
                            'end_date': end_date_format,
                            'price_residual': vourcher.price_residual,
                            'price_residual_no_compute': vourcher.price_residual,
                            'price_used': vourcher.price_used,
                            'price_change': 0,
                            'brand_id': vourcher.brand_id.id,
                            'partner': vourcher.partner_id.id,
                            'store_ids': vourcher.store_ids.ids,
                            'state': vourcher.state,
                            'start_date': start_date_format,
                            'apply_contemp_time': vourcher.apply_contemp_time,
                            'product_apply_ids': vourcher.product_apply_ids.ids,
                            'is_full_price_applies': vourcher.is_full_price_applies,
                            'using_limit': vourcher.program_voucher_id.using_limit,
                            'program_voucher_id': vourcher.program_voucher_id.id,
                            'product_voucher_name': vourcher.program_voucher_id.name,
                            'derpartment_name': vourcher.derpartment_id.name,
                            'state_app': vourcher.state_app,
                            'apply_many_times': vourcher.apply_many_times
                        }
                    })
                if not vourcher:
                    data.append({
                        'value': False,
                    })
        # program_valid = {
        # }
        # for rec in data:
        #     if rec['value']:
        #         if not rec['value']['program_voucher_id'] in program_valid.keys():
        #             program_valid[rec['value']['program_voucher_id']] = rec['value']['using_limit']
        #
        # for rec in data:
        #     if rec['value']:
        #         if not rec['value']['program_voucher_id'] in program.keys():
        #             program[rec['value']['program_voucher_id']] = rec['value']['using_limit']

        return data

    def _format_time_zone(self, time):
        utcmoment_naive = time
        utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
        # localFormat = "%Y-%m-%d %H:%M:%S"
        tz = 'Asia/Ho_Chi_Minh'
        create_Date = utcmoment.astimezone(pytz.timezone(tz))
        return create_Date

    # @api.constrains('phone_number')
    # def _check_phone(self):
    #     for rec in self:
    #         if rec.phone_number and not is_valid_phone_number(rec.phone_number):
    #             raise ValidationError(_('Invalid phone number - %s') % rec.phone_number)

    def check_due_date_voucher(self):
        now = datetime.now()
        vouchers = self.search([('state', '!=', 'expired')])
        if vouchers:
            for rec in vouchers:
                if rec.end_date and rec.end_date < now:
                    rec.status_latest = rec.state
                    rec.state = 'expired'

    @api.model
    def create(self, vals_list):
        if 'import_file' in self._context and self._context.get('import_file'):
            if 'phone_number' in vals_list and vals_list['phone_number']:
                phonenumbers_format = vals_list['phone_number'].replace(" ", "").replace("'", "").replace("’", "")
                partner = self.env['res.partner'].sudo().search(
                    [('phone', '=', phonenumbers_format), ('group_id', '=', self.env.ref('forlife_pos_app_member.partner_group_c', raise_if_not_found=False).id)],
                    limit=1)
                vals_list['phone_number'] = phonenumbers_format
                if not partner:
                    partner = self.env['res.partner'].sudo().create({
                        'name': phonenumbers_format,
                        'phone': phonenumbers_format,
                        'group_id': self.env.ref('forlife_pos_app_member.partner_group_c', raise_if_not_found=False).id,
                    })
                vals_list['partner_id'] = partner.id
        return super(Voucher, self).create(vals_list)
