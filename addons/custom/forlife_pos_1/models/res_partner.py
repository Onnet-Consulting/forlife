# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from phonenumbers import parse as parse_phone_number, format_number as format_phone_number, is_valid_number
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # FIXME check required fields and how to add value for already exist records
    group_id = fields.Many2one('res.partner.group', string='Group')
    job_ids = fields.Many2many('res.partner.job', string='Jobs')
    customer_type = fields.Selection([('employee', 'Employee'), ('app', 'App member'), ('retail', 'Retail')], string='Customer type')
    birthday = fields.Date(string='Birthday')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    ref = fields.Char(readonly=True)
    barcode = fields.Char(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for value in vals_list:
            group_id = value.get('group_id')
            if self.env.context.get('from_create_company'):
                group_id = self.env.ref('forlife_pos_1.partner_group_3').id
            if group_id:
                partner_group = self.env['res.partner.group'].browse(group_id)
                if partner_group.sequence_id:
                    value['ref'] = partner_group.sequence_id.next_by_id()
                else:
                    value['ref'] = partner_group.code + (value['ref'] or '')
            updated_phone_mobile = self.reformat_phone_and_mobile(value)
            value.update(updated_phone_mobile)
        res = super().create(vals_list)
        return res

    def write(self, values):
        updated_phone_mobile = self.reformat_phone_and_mobile(values)
        values.update(updated_phone_mobile)
        return super().write(values)

    @api.model
    def reformat_phone_and_mobile(self, values):
        # FIXME: check valid phone and mobile here
        phone = values.get('phone')
        mobile = values.get('mobile')
        phone = self.format_phone_number(phone) if phone else False
        mobile = self.format_phone_number(mobile) if mobile else False
        return dict(phone=phone, mobile=mobile)

    @api.constrains('phone')
    def _check_valid_phone(self):
        for record in self:
            phone = record.phone
            if phone and not self.check_valid_phone_number(phone):
                raise ValidationError(_('Invalid phone number!'))

    @api.constrains('mobile')
    def _check_valid_mobile(self):
        for record in self:
            mobile = record.mobile
            if mobile and not self.check_valid_phone_number(mobile):
                raise ValidationError(_('Invalid mobile number!'))

    @api.model
    def check_valid_phone_number(self, phone_number):
        try:
            parsed_number = parse_phone_number(phone_number)
        except NumberParseException as err:
            if err.error_type == NumberParseException.INVALID_COUNTRY_CODE:
                # the phone number without prefix region code -> default VieNam's phone number
                parsed_number = parse_phone_number(phone_number, 'VN')
            else:
                return False
        return is_valid_number(parsed_number)

    @api.model
    def format_phone_number(self, phone_number):
        try:
            parsed_number = parse_phone_number(phone_number)
            # keep region code for phone number with prefix region code
            return format_phone_number(parsed_number, PhoneNumberFormat.INTERNATIONAL)
        except NumberParseException:
            parsed_number = parse_phone_number(phone_number, 'VN')
            # return Vietnam's phone number
            return format_phone_number(parsed_number, PhoneNumberFormat.NATIONAL)
