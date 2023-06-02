# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.addons.forlife_pos_app_member.models.res_utility import get_valid_phone_number, is_valid_phone_number
from odoo.tools.safe_eval import safe_eval

import json
import uuid
import random

from lxml import etree


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_default_group_id(self):
        return self.env.ref('forlife_pos_app_member.partner_group_3', raise_if_not_found=False)

    group_id = fields.Many2one(
        'res.partner.group',
        string='Group', ondelete='restrict',
        default=lambda self: self.env.ref('forlife_pos_app_member.partner_group_system', raise_if_not_found=False),
        domain=lambda self:
        [('id', 'not in', [
            self.env.ref('forlife_pos_app_member.partner_group_3').id,
            self.env.ref('forlife_pos_app_member.partner_group_4').id,
            self.env.ref('forlife_pos_app_member.partner_group_5').id,
            self.env.ref('forlife_pos_app_member.partner_group_system').id,
        ])]
    )
    job_ids = fields.Many2many('res.partner.job', string='Jobs')
    retail_type_ids = fields.Many2many('res.partner.retail', string='Retail types', copy=False, ondelete='restrict')
    show_customer_type = fields.Boolean(compute='_compute_show_retail_types')
    birthday = fields.Date(string='Birthday')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')

    # FIXME: add readonly=True to ref field
    ref = fields.Char(copy=False, string='Mã')
    # FIXME: add readonly=True to barcode field
    barcode = fields.Char(company_dependent=False)  # a partner has only one barcode
    phone = fields.Char(copy=False, string='Phone #1')
    mobile = fields.Char(string='Phone #2')
    parsed_phone = fields.Char(compute="_compute_parsed_phone", string='Parsed phone')
    parsed_mobile = fields.Char(compute="_compute_parsed_mobile", string='Parsed mobile')

    _sql_constraints = [
        ('unique_barcode', 'UNIQUE(barcode)', 'Only one barcode occurrence by partner'),
        ('phone_number_group_uniq', 'unique(phone, group_id)',
         'The phone number must be unique in each Partner Group !'),
        ('unique_ref', 'UNIQUE(ref)', 'A Partner with the same "ref" already exists!')
    ]

    @api.depends('phone', 'create_uid')
    def _compute_parsed_phone(self):
        for rec in self:
            rec.parsed_phone = get_valid_phone_number(rec.phone) if rec.phone else False

    @api.depends('mobile')
    def _compute_parsed_mobile(self):
        for rec in self:
            rec.parsed_mobile = get_valid_phone_number(rec.mobile) if rec.mobile else False

    # FIXME: uncomment 2 constrains below when go production
    # @api.constrains('phone')
    # def _check_phone(self):
    #     for rec in self:
    #         if rec.phone and not is_valid_phone_number(rec.phone):
    #             raise ValidationError(_('Invalid phone number - %s') % rec.phone)
    #
    @api.constrains('group_id', 'phone')
    def _check_required_phone_in_group(self):
        retail_customer_group = self.env.ref('forlife_pos_app_member.partner_group_c')
        for rec in self:
            if not rec.phone and rec.group_id == retail_customer_group:
                raise ValidationError(_("Phone number is required for group %s") % retail_customer_group.name)

    #
    # @api.constrains('mobile')
    # def _check_mobile(self):
    #     for rec in self:
    #         if rec.mobile and not is_valid_phone_number(rec.mobile):
    #             raise ValidationError(_('Invalid mobile number - %s') % rec.mobile)

    @api.depends('group_id')
    def _compute_show_retail_types(self):
        for record in self:
            record.show_customer_type = record.group_id == self.env.ref('forlife_pos_app_member.partner_group_c')

    @api.model
    def generate_partner_barcode(self):
        while True:
            random_str = str(uuid.uuid4().int)
            barcode = ''.join(random.sample(random_str, k=16))  # pick 16 random digits
            self._cr.execute("SELECT 1 FROM res_partner WHERE barcode = %s", [barcode])
            if not self._cr.fetchall():
                return barcode

    @api.model
    def get_app_retail_type(self):
        env_context = self.env.context
        app_brand_code = env_context.get('is_app_customer') and env_context.get('brand_code')
        if app_brand_code:
            app_retail_type_id = self.env['res.partner.retail'].search(
                [('brand_id.code', '=', app_brand_code), ('retail_type', '=', 'app')], limit=1).id
        else:
            app_retail_type_id = False
        return app_retail_type_id

    @api.model_create_multi
    def create(self, vals_list):
        env_context = self.env.context
        app_retail_type_id = self.get_app_retail_type()

        for value in vals_list:
            group_id = value.get('group_id')
            # add retail type for App customer
            if app_retail_type_id:
                value.update({
                    'retail_type_ids': [(4, app_retail_type_id)],
                    'barcode': self.generate_partner_barcode()
                })
                group_id = self.env.ref('forlife_pos_app_member.partner_group_c').id

            # generate ref
            if env_context.get('from_create_company'):
                group_id = self.env.ref('forlife_pos_app_member.partner_group_3').id
            if group_id:
                value['group_id'] = group_id
                partner_group = self.env['res.partner.group'].browse(group_id)
                if value.get('ref') or not partner_group.sequence_id:
                    continue
                value['ref'] = partner_group.sequence_id.next_by_id()

        return super().create(vals_list)

    def write(self, values):
        app_retail_type_id = self.get_app_retail_type()
        if app_retail_type_id:
            if len(self) > 1:
                raise ValueError("Expected singleton: %s" % self)
            values.update({'retail_type_ids': [(4, app_retail_type_id)]})
            if not self.barcode:
                values.update({
                    'barcode': self.generate_partner_barcode(),
                })

        return super().write(values)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        env_context = self.env.context
        if env_context.get('is_app_customer'):
            return super(ResPartner, self).search(
                expression.AND([[('group_id', '=', self.env.ref('forlife_pos_app_member.partner_group_c').id)], args]),
                offset=offset, limit=limit, order=order, count=count
            )
        return super(ResPartner, self).search(args, offset=offset, limit=limit, order=order, count=count)

    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        # remove default group_id value on views, keep on other source (api, controller ...)
        if self._context.get('partner_action'):
            res.pop('group_id', False)
        return res

    @api.model
    def _add_partner_action_context(self):
        partner_actions = self.env['ir.actions.act_window'].search([('res_model', '=', 'res.partner')])
        additional_context = {'partner_action': True}
        for action in partner_actions:
            context = safe_eval(action.context)
            context.update(additional_context)
            action.context = context
        return True
