# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MemberCard(models.Model):
    _name = 'member.card'
    _description = 'Member Card'
    _inherit = ['mail.thread']

    brand_id = fields.Many2one("res.brand", string="Brand", required=True, default=lambda s: s.env['res.brand'].search([('code', '=', s._context.get('default_brand_code', ''))], limit=1))
    brand_code = fields.Char('Brand Code', required=True)
    name = fields.Char('Program Name', required=True)
    is_register = fields.Boolean('Is Register', default=False)
    register_from_date = fields.Date('Register From Date')
    register_to_date = fields.Date('Register To Date')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    is_all_store = fields.Boolean('Is All Store', default=True)
    store_ids = fields.Many2many('store', string='Stores Apply')
    time_set_rank = fields.Integer('Time Set Rank', default=0)
    customer_group_ids = fields.Many2many('res.partner.group', string='Customer Group')
    payment_method_ids = fields.Many2many('pos.payment.method', string='POS Payment Method')
    card_rank_id = fields.Many2one('card.rank', string='Rank', copy=False)
    min_turnover = fields.Integer('Min Turnover')
    max_turnover = fields.Integer('Max Turnover')
    original_price = fields.Integer('Original Price')
    apply_value_from_1 = fields.Integer('Apply Value From1')
    apply_value_to_1 = fields.Integer('Apply Value To1')
    apply_value_from_2 = fields.Integer('Apply Value From2')
    apply_value_to_2 = fields.Integer('Apply Value To2')
    apply_value_from_3 = fields.Integer('Apply Value From3')
    apply_value_to_3 = fields.Integer('Apply Value To3')

    _sql_constraints = [
        ("rank_brand_uniq", "unique(card_rank_id, brand_id)", "Card Rank of brand already exist !"),
    ]

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


class FormUpdateStore(models.TransientModel):
    _name = 'form.update.store'
    _description = 'Form Update Store'

    member_card_id = fields.Many2one('member.card', string='Member Card')
    store_ids = fields.Many2many('store', string='Stores Apply')

    def btn_ok(self):
        self.member_card_id.sudo().write({
            'store_ids': [(6, 0, self.store_ids.ids)],
        })
