# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz
import copy


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
    is_all_store = fields.Boolean('Is All Store', default=True, tracking=True)
    store_ids = fields.Many2many('store', string='Stores Apply')
    time_set_rank = fields.Integer('Time Set Rank', default=180, tracking=True)
    customer_group_ids = fields.Many2many('res.partner.group', string='Customer Group')
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method')
    card_rank_id = fields.Many2one('card.rank', string='Rank', tracking=True)
    min_turnover = fields.Integer('Turnover', tracking=True)
    original_price = fields.Integer('Original Price')
    apply_value_from_1 = fields.Integer('Apply Value From1')
    apply_value_to_1 = fields.Integer('Apply Value To1')
    value1 = fields.Integer('Value 1')
    apply_value_from_2 = fields.Integer('Apply Value From2')
    apply_value_to_2 = fields.Integer('Apply Value To2')
    value2 = fields.Integer('Value 2')
    apply_value_from_3 = fields.Integer('Apply Value From3')
    apply_value_to_3 = fields.Integer('Apply Value To3')
    value3 = fields.Integer('Value 3')
    active = fields.Boolean('Active', default=True, tracking=True)

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

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
        return ['&', '&', ('brand_id', '=', self.brand_id.id), ('id', '!=', self.id),
                '|', '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
                '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date)]

    def btn_add_stores(self):
        ctx = dict(self._context)
        ctx.update({
            'default_member_card_id': self.id,
            'default_store_ids': self.store_ids.ids,
            'brand_id': self.brand_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Store'),
            'res_model': 'form.update.store',
            'target': 'new',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_customer_card_rank.form_update_store_view_form').id, 'form']],
            'context': ctx,
        }

    def action_inactive_member_card_program(self):
        res = self.search([('active', '=', True), ('to_date', '<', fields.Date.today())])
        if res:
            res.sudo().write({
                'active': False,
            })

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for line in res:
            if line.store_ids:
                message = {
                    'added': _('Store added: %s') % ', '.join(line.store_ids.mapped('name')),
                    'time': fields.Datetime.now().astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y %H:%M:%S')
                }
                line.message_post_with_view(
                    'forlife_customer_card_rank.message_update_stores',
                    values=message
                )
        return res

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
            'default_is_all_store': self.is_all_store,
            'default_store_ids': self.store_ids.ids,
            'default_time_set_rank': self.time_set_rank,
            'default_customer_group_ids': self.customer_group_ids.ids,
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


class FormUpdateStore(models.TransientModel):
    _name = 'form.update.store'
    _description = 'Form Update Store'

    member_card_id = fields.Many2one('member.card', string='Member Card')
    store_ids = fields.Many2many('store', string='Stores Apply')

    def btn_ok(self):
        store_add = self.store_ids - self.member_card_id.store_ids
        store_del = self.member_card_id.store_ids - self.store_ids
        message = {}
        if store_add:
            message.update({'added': _('Store added: %s') % ', '.join(store_add.mapped('name'))})
        if store_del:
            message.update({'deleted': _('Store deleted: %s') % ', '.join(store_del.mapped('name'))})
        if message:
            message.update({'time': fields.Datetime.now().astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y %H:%M:%S')})
            self.member_card_id.message_post_with_view(
                'forlife_customer_card_rank.message_update_stores',
                values=message
            )
            self.member_card_id.sudo().write({
                'store_ids': [(6, 0, self.store_ids.ids)],
            })
