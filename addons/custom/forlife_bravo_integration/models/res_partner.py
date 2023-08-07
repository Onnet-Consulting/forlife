# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoMany2oneField, BravoIntegerField, BravoDecimalField


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'bravo.model']
    _bravo_table = 'B20Customer'
    _bravo_field_sync = [
        'ref', 'name', 'phone', 'email', 'vat', 'contact_address_complete', 'group_id', 'credit_limit', 'property_purchase_currency_id'
    ]

    br_1 = BravoCharField(odoo_name="ref", bravo_name="Code", identity=True)
    br_2 = BravoCharField(odoo_name="name", bravo_name="Name")
    br_3 = BravoCharField(odoo_name="phone", bravo_name="Tel")
    br_4 = BravoCharField(odoo_name="email", bravo_name="Email")
    br_5 = BravoCharField(odoo_name="vat", bravo_name="TaxRegNo")
    br_6 = BravoCharField(odoo_name="contact_address_complete", bravo_name="Address",
                          odoo_depend_fields=('street', 'zip', 'city', 'state_id', 'country_id'))
    br_7 = BravoIntegerField(bravo_default=0, bravo_name="IsGroup")
    br_8 = BravoMany2oneField('res.partner.group', odoo_name='group_id', bravo_name='ParentCode', field_detail='code')
    br_9 = BravoDecimalField(odoo_name='credit_limit', bravo_name='CreditLimit')
    br_10 = BravoMany2oneField('res.currency', odoo_name='property_purchase_currency_id',
                               bravo_name='CurrencyCode', field_detail='name')

    def bravo_get_filter_domain(self):
        partner_group_c = self.env.ref('forlife_pos_app_member.partner_group_c').id
        partner_group_system = self.env.ref('forlife_pos_app_member.partner_group_system').id
        return [('group_id', 'not in', [partner_group_c, partner_group_system]), ('group_id', '!=', False)]


class ResPartnerGroup(models.Model):
    _name = 'res.partner.group'
    _inherit = ['res.partner.group', 'bravo.model']
    _bravo_table = 'B20Customer'
    _bravo_field_sync = ['code', 'name']

    br_1 = BravoCharField(odoo_name="code", bravo_name="Code", identity=True)
    br_2 = BravoCharField(odoo_name="name", bravo_name="Name")
    br_3 = BravoIntegerField(bravo_default=1, bravo_name="IsGroup")

    @api.model
    def bravo_push_existing_groups(self):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return True
        exist_groups = self.env.ref("forlife_pos_app_member.partner_group_1") + \
                       self.env.ref("forlife_pos_app_member.partner_group_2") + \
                       self.env.ref("forlife_pos_app_member.partner_group_3") + \
                       self.env.ref("forlife_pos_app_member.partner_group_4") + \
                       self.env.ref("forlife_pos_app_member.partner_group_5") + \
                       self.env.ref("forlife_pos_app_member.partner_group_6")
        exist_groups.sudo().with_delay(channel="root.Bravo").bravo_insert_with_check_existing()
        return True

    def bravo_get_filter_domain(self):
        partner_group_c = self.env.ref('forlife_pos_app_member.partner_group_c').id
        partner_group_system = self.env.ref('forlife_pos_app_member.partner_group_system').id
        return [('id', 'not in', [partner_group_c, partner_group_system])]
