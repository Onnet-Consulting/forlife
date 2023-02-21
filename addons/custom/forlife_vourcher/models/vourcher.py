from odoo import api, fields, models
import phonenumbers
from odoo.addons.forlife_pos_app_member.models.res_utility import get_valid_phone_number, is_valid_phone_number


class Vourcher(models.Model):
    _name = 'vourcher.vourcher'

    _description = 'Vourcher'

    name = fields.Char('Code', required=True)
    program_vourcher_id = fields.Many2one('program.vourcher', 'Program name')
    currency_id = fields.Many2one('res.currency', related='product_vourcher_id.currency_id')  # related currency of program vourcher
    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True)
    state = fields.Selection([('new', 'New'), ('sold', 'Sold'), ('valid', 'Valid'), ('off value', 'Off Value'), ('expired', 'Expired')], string='State', required=True)
    price = fields.Monetary('Mệnh giá')
    price_used = fields.Monetary('Giá trị đã dùng')
    price_residual = fields.Monetary('Giá trị còn lại')
    start_date = fields.Datetime('Start date')
    end_date = fields.Datetime('End date')
    apply_many_times = fields.Boolean('Apply many times', default=False)

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời')

    purchase_id = fields.Many2one('purchase.order', 'Đơn hàng mua')

    state_app = fields.Boolean('Trạng thái App')

    sale_id = fields.Many2one('sale.order', 'Đơn hàng bán')

    order_pos = fields.Many2one('pos.order', 'Đơn hàng POS')

    order_use = fields.Many2one('pos.order', 'Đơn hàng sử dụng')

    partner_id = fields.Many2one('res.partner')
    phone_number = fields.Char(copy=False, string='Phone')

    product_vourcher_id = fields.Many2one('product.template', 'Product Vourcher')

    derpartment_id = fields.Many2one('hr.department', 'Department Code', required=True)

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
