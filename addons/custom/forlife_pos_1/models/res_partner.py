# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from phonenumbers import parse as parse_phone_number, format_number, is_valid_number
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException
import uuid


class ResPartner(models.Model):
    _inherit = 'res.partner'

    group_id = fields.Many2one('res.partner.group', string='Group', copy=False)
    job_ids = fields.Many2many('res.partner.job', string='Jobs')
    retail_type_ids = fields.Many2many('res.partner.retail', string='Retail types', copy=False)
    show_customer_type = fields.Boolean(compute='_compute_show_retail_types')
    birthday = fields.Date(string='Birthday')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    ref = fields.Char(readonly=True)
    barcode = fields.Char(readonly=True, company_dependent=False)  # a partner has only one barcode
    phone = fields.Char(copy=False)
    parsed_phone = fields.Char(compute="_compute_parsed_phone", string='Parsed phone')
    parsed_mobile = fields.Char(compute="_compute_parsed_mobile", string='Parsed mobile')

    _sql_constraints = [
        ('unique_barcode', 'UNIQUE(barcode)', 'Only one barcode occurrence by partner'),
        ('phone_number_group_uniq', 'unique(phone, group_id)', 'The phone number must be unique in each Partner Group !'),
    ]

    @api.depends('phone')
    def _compute_parsed_phone(self):
        for rec in self:
            rec.parsed_phone = self.get_valid_phone_number(rec.phone) if rec.phone else False

    @api.depends('mobile')
    def _compute_parsed_mobile(self):
        for rec in self:
            rec.parsed_mobile = self.get_valid_phone_number(rec.mobile) if rec.mobile else False

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            if rec.phone and not self.is_valid_phone_number(rec.phone):
                raise ValidationError(_('Invalid phone number - %s') % rec.phone)

    @api.constrains('mobile')
    def _check_mobile(self):
        for rec in self:
            if rec.mobile and not self.is_valid_phone_number(rec.mobile):
                raise ValidationError(_('Invalid mobile number - %s') % rec.mobile)

    @api.depends('group_id')
    def _compute_show_retail_types(self):
        for record in self:
            record.show_customer_type = record.group_id == self.env.ref('forlife_pos_1.partner_group_c')

    @api.model
    def generate_partner_barcode(self):
        return str(uuid.uuid1().int >> 74)  # 16 digits

    @api.model
    def get_app_retail_type(self):
        env_context = self.env.context
        app_brand_code = env_context.get('is_app_customer') and env_context.get('brand_code')
        if app_brand_code:
            app_retail_type_id = self.env['res.partner.retail'].search([('brand_id.code', '=', app_brand_code), ('retail_type', '=', 'app')], limit=1).id
        else:
            app_retail_type_id = False
        return app_retail_type_id

    @api.model_create_multi
    def create(self, vals_list):
        env_context = self.env.context
        app_retail_type_id = self.get_app_retail_type()

        for value in vals_list:
            # generate ref
            group_id = value.get('group_id')
            if env_context.get('from_create_company'):
                group_id = self.env.ref('forlife_pos_1.partner_group_3').id
            if group_id:
                partner_group = self.env['res.partner.group'].browse(group_id)
                if partner_group.sequence_id:
                    value['ref'] = partner_group.sequence_id.next_by_id()
                else:
                    value['ref'] = partner_group.code + (value['ref'] or '')
            # add retail type for App customer
            if app_retail_type_id:
                value.update({'retail_type_ids': [(4, app_retail_type_id)]})
                value.update({'barcode': self.generate_partner_barcode()})

        res = super().create(vals_list)
        return res

    def write(self, values):
        app_retail_type_id = self.get_app_retail_type()
        if app_retail_type_id:
            if len(self) > 1:
                raise ValueError("Expected singleton: %s" % self)
            if not self.barcode:
                values.update({'barcode': self.generate_partner_barcode()})
        return super().write(values)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        env_context = self.env.context
        if env_context.get('is_app_customer'):
            return super(ResPartner, self).search(
                expression.AND([[('group_id', '=', self.env.ref('forlife_pos_1.partner_group_c').id)], args]),
                offset=offset, limit=limit, order=order, count=count
            )
        return super(ResPartner, self).search(args, offset=offset, limit=limit, order=order, count=count)

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

    @api.model
    def is_valid_phone_number(self, phone_number):
        try:
            parsed_number = parse_phone_number(phone_number)
        except NumberParseException as err:
            if err.error_type == NumberParseException.INVALID_COUNTRY_CODE:
                # the phone number without prefix region code -> default VieNam's phone number
                parsed_number = parse_phone_number(phone_number, 'VN')
            else:
                return False
        if not is_valid_number(parsed_number):
            return False
        return True
