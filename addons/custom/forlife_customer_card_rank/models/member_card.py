# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import copy
import base64
from datetime import date


class MemberCard(models.Model):
    _name = 'member.card'
    _description = 'Member Card'
    _inherit = ['mail.thread']
    _order = 'to_date desc, min_turnover desc'

    brand_id = fields.Many2one("res.brand", string="Brand", required=True, default=lambda s: s.env['res.brand'].search([('code', '=', s._context.get('default_brand_code', ''))], limit=1))
    brand_code = fields.Char('Brand Code', required=True)
    name = fields.Char('Program Name', required=True)
    is_register = fields.Boolean('Is Register', default=False)
    register_from_date = fields.Date('Register From Date')
    register_to_date = fields.Date('Register To Date')
    from_date = fields.Date('Time Apply', copy=False, tracking=True)
    to_date = fields.Date('To Date', copy=False, tracking=True)
    time_set_rank = fields.Integer('Time Set Rank', default=180, tracking=True)
    customer_group_id = fields.Many2one('res.partner.group', string='Customer Group', default=lambda f: f.env['res.partner.group'].search([('code', '=', 'C')]).id)
    partner_retail_ids = fields.Many2many('res.partner.retail', string='Customer Retail Types')
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method')
    card_rank_id = fields.Many2one('card.rank', string='Rank', tracking=True)
    min_turnover = fields.Float('Turnover', tracking=True, digits=(16, 0))
    retail_type_not_apply_ids = fields.Many2many('res.partner.retail', relation="retail_type_not_apply_rel", string='Retail type not apply')
    original_price = fields.Float('Original Price')
    apply_value_from_1 = fields.Float('Apply Value From1')
    apply_value_to_1 = fields.Float('Apply Value To1')
    value1 = fields.Float('Value 1')
    apply_value_from_2 = fields.Float('Apply Value From2')
    apply_value_to_2 = fields.Float('Apply Value To2')
    value2 = fields.Float('Value 2')
    apply_value_from_3 = fields.Float('Apply Value From3')
    apply_value_to_3 = fields.Float('Apply Value To3')
    value3 = fields.Float('Value 3')
    active = fields.Boolean('Active', default=True, tracking=True)
    qty_order_rank = fields.Integer('Order Rank', compute='_compute_qty_order')
    qty_order_discount = fields.Integer('Order Discount', compute='_compute_qty_order')
    journal_id = fields.Many2one('account.journal', string='Journal', tracking=True)
    discount_account_id = fields.Many2one('account.account', string='Discount Account', tracking=True)
    value_account_id = fields.Many2one('account.account', string='Value Account', tracking=True)
    value_remind = fields.Float('Value Remind', tracking=True, digits=(16, 0))
    customer_not_apply = fields.Binary(string='Customer not apply', compute='_compute_customer', store=True)
    point_coefficient_first_order = fields.Integer('Point Coefficient First Order')
    point_plus_first_order = fields.Integer('Point Plus First Order')

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    @api.constrains('point_coefficient_first_order', 'point_plus_first_order')
    def _check_point_first_order(self):
        for item in self:
            if item.point_coefficient_first_order > 0 and item.point_plus_first_order > 0:
                raise ValidationError(
                    _("Please enter a value greater than 0 in either field 'Point Coefficient First Order' or 'Point Plus First Order'."))

    def _compute_qty_order(self):
        for line in self:
            line.qty_order_rank = self.env['partner.card.rank.line'].search_count([
                ('partner_card_rank_id.brand_id', '=', line.brand_id.id),
                ('order_id', '!=', False), ('program_cr_id', '=', line.id)])
            line.qty_order_discount = self.env['pos.order'].search_count([('card_rank_program_id', '=', line.id)])

    @api.depends('retail_type_not_apply_ids')
    def _compute_customer(self):
        partners = self.env['res.partner'].search_read([('retail_type_ids', '!=', False)], ['id', 'retail_type_ids'])
        for line in self:
            if line.retail_type_not_apply_ids:
                line.customer_not_apply = base64.b64encode((json.dumps([x['id'] for x in partners if any([i in x['retail_type_ids'] for i in line.retail_type_not_apply_ids.ids])])).encode('utf-8'))
            else:
                line.customer_not_apply = False

    @api.constrains("from_date", "to_date", 'active', 'min_turnover', 'card_rank_id')
    def validate_time(self):
        for record in self:
            domain_master = record.get_master_domain()
            check_time_dm = copy.copy(domain_master)
            check_time_dm.insert(3, ('card_rank_id', '=', record.card_rank_id.id))
            check_time_dm.insert(0, '&')
            check_time_exist = self.search(check_time_dm)
            if check_time_exist:
                raise ValidationError(_("Time of '%s' rank is overlapping.") % record.card_rank_id.name)

            previous_rank_id, next_rank_id = self.env['card.rank'].get_ranking_around(record.card_rank_id.priority)
            if next_rank_id:
                for rank_id in next_rank_id:
                    next_rank_dm = copy.copy(domain_master)
                    next_rank_dm.insert(3, ('min_turnover', '<=', record.min_turnover))
                    next_rank_dm.insert(4, ('card_rank_id', '=', rank_id))
                    next_rank_dm.insert(0, '&')
                    next_rank_dm.insert(0, '&')
                    check_next_exist = self.search(next_rank_dm, order='min_turnover asc', limit=1)
                    if check_next_exist:
                        raise ValidationError(_("Turnover of '%s' rank must be less than Turnover of '%s' rank '%s'"
                                                ) % (record.card_rank_id.name, check_next_exist.card_rank_id.name, '{:,.0f}'.format(check_next_exist.min_turnover)))
            if previous_rank_id:
                for rank_id in previous_rank_id:
                    previous_rank_dm = copy.copy(domain_master)
                    previous_rank_dm.insert(3, ('min_turnover', '>=', record.min_turnover))
                    previous_rank_dm.insert(4, ('card_rank_id', '=', rank_id))
                    previous_rank_dm.insert(0, '&')
                    previous_rank_dm.insert(0, '&')
                    check_previous_exist = self.search(previous_rank_dm, order='min_turnover desc', limit=1)
                    if check_previous_exist:
                        raise ValidationError(_("Turnover of '%s' rank must be greater than Turnover of '%s' rank '%s'"
                                                ) % (record.card_rank_id.name, check_previous_exist.card_rank_id.name, '{:,.0f}'.format(check_previous_exist.min_turnover)))

    def get_master_domain(self):
        self.ensure_one()
        return ['&', '&', '&', ('brand_id', '=', self.brand_id.id), ('id', '!=', self.id), ('active', 'in', (True, False)),
                '|', '|', '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
                '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date),
                '&', ('from_date', '>', self.from_date), ('to_date', '<', self.to_date)]

    def action_inactive_member_card_program(self):
        res = self.search([('active', '=', True), ('to_date', '<', fields.Date.today())])
        if res:
            res.sudo().write({
                'active': False,
            })

    def get_member_card_by_date(self, date, brand_id):
        return self.search([('brand_id', '=', brand_id), ('from_date', '<=', date), ('to_date', '>=', date)])

    def btn_duplicate_member_card(self):
        self.ensure_one()
        ctx = dict(self._context)
        ctx.update({
            'default_brand_id': self.brand_id.id,
            'default_brand_code': self.brand_code,
            'default_name': self.name,
            'default_is_register': self.is_register,
            'default_register_from_date': self.register_from_date,
            'default_register_to_date': self.register_to_date,
            'default_from_date': self.from_date,
            'default_to_date': self.to_date,
            'default_time_set_rank': self.time_set_rank,
            'default_customer_group_id': self.customer_group_id.id,
            'default_partner_retail_ids': self.partner_retail_ids.ids,
            'default_payment_method_ids': self.payment_method_ids.ids,
            'default_card_rank_id': self.card_rank_id.id,
            'default_min_turnover': self.min_turnover,
            'default_original_price': self.original_price,
            'default_apply_value_from_1': self.apply_value_from_1,
            'default_apply_value_from_2': self.apply_value_from_2,
            'default_apply_value_from_3': self.apply_value_from_3,
            'default_apply_value_to_1': self.apply_value_to_1,
            'default_apply_value_to_2': self.apply_value_to_2,
            'default_apply_value_to_3': self.apply_value_to_3,
            'default_journal_id': self.journal_id.id,
            'default_discount_account_id': self.discount_account_id.id,
            'default_value_account_id': self.value_account_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Card'),
            'res_model': 'member.card',
            'target': 'current',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_customer_card_rank.member_card_view_form').id, 'form']],
            'context': ctx,
        }

    def action_view_pos_order(self):
        self.ensure_one()
        domain = {
            'order_discount': [('card_rank_program_id', '=', self.id)],
            'order_rank': [('id', 'in', self.env['partner.card.rank.line'].search([
                ('partner_card_rank_id.brand_id', '=', self.brand_id.id),
                ('order_id', '!=', False), ('program_cr_id', '=', self.id)]).order_id.ids)],
        }
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')
        action['domain'] = domain.get(self._context.get('domain_order')) or [('id', 'in', [])]
        return action

    def unlink(self):
        for line in self:
            if line.qty_order_rank > 0:
                raise ValidationError(_("You can't delete the card rank program that delivered the order"))
        return super().unlink()

    def name_get(self):
        result = super().name_get()
        if self._context.get('display_rank_name', False):
            result = []
            for program in self:
                result.append((program.id, program.card_rank_id.name))
        return result

    def check_registering_tax(self):
        return self.is_register and self.register_from_date <= date.today() <= self.register_to_date
