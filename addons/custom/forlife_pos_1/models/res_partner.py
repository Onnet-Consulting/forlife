# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from phonenumbers import parse as parse_phone_number, format_number, is_valid_number
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException
import uuid

class ResPartner(models.Model):
    _inherit = 'res.partner'

    group_id = fields.Many2one('res.partner.group', string='Group')
    job_ids = fields.Many2many('res.partner.job', string='Jobs')
    retail_type_ids = fields.Many2many('res.partner.retail', string='Retail types')
    show_customer_type = fields.Boolean(compute='_compute_show_retail_types')
    birthday = fields.Date(string='Birthday')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    ref = fields.Char(readonly=True)
    barcode = fields.Char(readonly=True)

    def generate_barcode(self):
        # TODO: add function generate barcode when create app customer
        new_barcode = (str(uuid.uuid1().int >> 74))

    _sql_constraints = [
        ('unique_barcode', 'UNIQUE(barcode)', 'Only one barcode occurrence by partner')
    ]

    @api.depends('group_id')
    def _compute_show_retail_types(self):
        for record in self:
            record.show_customer_type = record.group_id == self.env.ref('forlife_pos_1.partner_group_c')

    @api.model_create_multi
    def create(self, vals_list):
        env_context = self.env.context
        # FIXME: when create partner on PoS, we must update context with is_pos_customer and brand_id
        tokyolife_brand_id = self.env.ref('forlife_point_of_sale.brand_tokyolife_id').id
        brand_id = env_context.get('is_pos_customer') and (env_context.get('brand_id') or tokyolife_brand_id)
        default_retail_type = self.env['res.partner.retail'].search(
            [('brand_id', '=', brand_id), ('retail_type', '=', 'customer')]
        ) if brand_id else False

        for value in vals_list:
            group_id = value.get('group_id')
            if env_context.get('from_create_company'):
                group_id = self.env.ref('forlife_pos_1.partner_group_3').id
            if group_id:
                partner_group = self.env['res.partner.group'].browse(group_id)
                if partner_group.sequence_id:
                    value['ref'] = partner_group.sequence_id.next_by_id()
                else:
                    value['ref'] = partner_group.code + (value['ref'] or '')
            sanitized_phone_mobile = self.sanitize_phone_and_mobile(value)
            value.update(sanitized_phone_mobile)
            # add default retail type for POS customer
            if not value.get('retail_type_ids') and default_retail_type:
                value.update({'retail_type_ids': [(4, default_retail_type.id)]})

        res = super().create(vals_list)
        return res

    def write(self, values):
        sanitized_phone_mobile = self.sanitize_phone_and_mobile(values)
        values.update(sanitized_phone_mobile)
        return super().write(values)

    @api.model
    def sanitize_phone_and_mobile(self, values):
        if self.env.context.get('initial_write_action'):
            # don't validate phone and mobile of partner created by system
            return {}
        new_value = {}
        if 'phone' in values:
            phone = values.get('phone')
            phone = self.get_valid_phone_number(phone) if phone else False
            new_value.update(dict(phone=phone))
        if 'mobile' in values:
            mobile = values.get('mobile')
            mobile = self.get_valid_phone_number(mobile) if mobile else False
            new_value.update(dict(mobile=mobile))
        return new_value

    @api.model
    def get_valid_phone_number(self, phone_number):
        error_message = _('Invalid phone (mobile) number - %s') % phone_number
        try:
            parsed_number = parse_phone_number(phone_number)
            format_type = PhoneNumberFormat.INTERNATIONAL  # keep region code
        except NumberParseException as err:
            if err.error_type == NumberParseException.INVALID_COUNTRY_CODE:
                # the phone number without prefix region code -> default VieNam's phone number
                parsed_number = parse_phone_number(phone_number, 'VN')
                format_type = PhoneNumberFormat.NATIONAL
            else:
                raise ValidationError(error_message)
        if not is_valid_number(parsed_number):
            raise ValidationError(error_message)
        return format_number(parsed_number, format_type)
