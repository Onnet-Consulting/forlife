from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
import datetime
import logging

_logger = logging.getLogger(__name__)


class Contact(models.Model):
    _inherit = 'res.partner'

    is_purchased_of_forlife = fields.Boolean('Is Purchased Forlife')
    is_purchased_of_format = fields.Boolean('Is Purchased Format')
    is_member_app_forlife = fields.Boolean('Is Member App?', compute='_compute_member_pos', store=True)
    is_member_app_format = fields.Boolean('Is Member App?', compute='_compute_member_pos', store=True)
    reset_day_of_point_forlife = fields.Datetime('Day Reset Forlife', readonly=True)
    reset_day_of_point_format = fields.Datetime('Day Reset Format', readonly=True)
    total_points_available_forlife = fields.Integer('Total Points Availible', compute='compute_point_total')
    total_points_available_format = fields.Integer('Total Points Availible', compute='compute_point_total')
    history_points_format_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=', 'format')], readonly=True)
    history_points_forlife_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=', 'forlife')], readonly=True)

    point_forlife_reseted = fields.Boolean('Forlife was reseted', default=False)
    point_format_reseted = fields.Boolean('Format was reseted', default=False)


    @api.depends('history_points_format_ids', 'history_points_forlife_ids')
    def compute_point_total(self):
        for rec in self:
            rec.total_points_available_forlife = sum([x.points_store for x in rec.history_points_forlife_ids])
            rec.total_points_available_format = sum([x.points_store for x in rec.history_points_format_ids])

    # def _check_is_purchased(self):
    #     brand_tokyolife = self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id
    #     brand_format = self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id
    #     pos_partner_tokyo_exits = self.env['pos.order'].sudo().search([('partner_id', '=', self.id), ('program_store_point_id.brand_id.id','=',brand_tokyolife)], limit=2)
    #     pos_partner_format_exits = self.env['pos.order'].sudo().search([('partner_id', '=', self.id), ('program_store_point_id.brand_id.id','=',brand_format)], limit=2)
    #     if len(pos_partner_tokyo_exits) == 1:
    #         is_purchased_of_forlife = False
    #     else:
    #         is_purchased_of_forlife = True
    #     if len(pos_partner_format_exits) == 1:
    #         is_purchased_of_format = False
    #     else:
    #         is_purchased_of_format = True
    #     return is_purchased_of_format, is_purchased_of_forlife

    @api.depends('group_id', 'retail_type_ids')
    def _compute_member_pos(self):
        for rec in self:
            if rec.group_id and rec.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_c', raise_if_not_found=False).id:
                if self.env.ref('forlife_pos_app_member.res_partner_retail_tokyolife_app', raise_if_not_found=False).id in rec.retail_type_ids.ids:
                    rec.is_member_app_forlife = True
                if self.env.ref('forlife_pos_app_member.res_partner_retail_format_app', raise_if_not_found=False).id in rec.retail_type_ids.ids:
                    rec.is_member_app_format = True
            else:
                rec.is_member_app_forlife = False
                rec.is_member_app_format = False

    def _compute_reset_day(self, date_order, day_expiration, branch):
        timedelta_in_days = datetime.timedelta(days=day_expiration)
        if branch == 'forlife':
            if (self.reset_day_of_point_forlife and date_order + timedelta_in_days > self.reset_day_of_point_forlife) \
                    or not self.reset_day_of_point_forlife:
                self.reset_day_of_point_forlife = date_order + timedelta_in_days
                # Flag reset
                self.point_forlife_reseted = False
        if branch == 'format':
            if (self.reset_day_of_point_format and date_order + timedelta_in_days > self.self.reset_day_of_point_format)\
                    or not self.reset_day_of_point_format:
                self.reset_day_of_point_format = date_order + timedelta_in_days
                # Flag reset
                self.point_format_reseted = False
        return True
    #
    # MFL2201ER-282
    #

    @api.onchange('reset_day_of_point_forlife')
    def _onchange_reset_day_of_point_forlife(self):
        self.point_forlife_reseted = False

    @api.onchange('reset_day_of_point_format')
    def _onchange_reset_day_of_point_format(self):
        self.point_format_reseted = False

    def reset_partner_point(self):
        now = fields.Datetime.now()
        history_point_obj = self.env['partner.history.point']
        account_move_obj = self.env['account.move']
        brand_forlife_id = self.env['res.brand'].search([('code', '=', 'TKL')], limit=1)
        brand_format_id = self.env['res.brand'].search([('code', '=', 'FMT')], limit=1)
        point_promotion_forlife_id = self.env['points.promotion'].search([('brand_id', '=', brand_forlife_id.id), ('state', '=', 'in_progress')], limit=1)
        point_promotion_format_id = self.env['points.promotion'].search([('brand_id', '=', brand_format_id.id), ('state', '=', 'in_progress')], limit=1)

        # Reset Forlife point
        reset_forlife_partners = self.search([('reset_day_of_point_forlife', '<=', now), ('point_forlife_reseted', '=', False)])
        if reset_forlife_partners:
            # vals = {'point_forlife_reseted': True}
            vals = {}
            # create journal entries
            if point_promotion_forlife_id:
                move_line_vals = [(0, 0, {
                    'account_id': point_promotion_forlife_id.point_customer_id.property_account_receivable_id.id,
                    'partner_id': point_promotion_forlife_id.point_customer_id.id,
                    'name': partner.name,
                    'debit': partner.total_points_available_forlife * 1000,
                    'credit': 0
                }) for partner in reset_forlife_partners]
                move_line_vals += [(0, 0, {
                    'account_id': point_promotion_forlife_id.acc_accumulate_points_id.id,
                    'debit': 0,
                    'credit': sum(reset_forlife_partners.mapped('total_points_available_forlife')) * 1000
                })]
                move_vals = {
                    'ref': 'TokyoLife',
                    'date': now.date(),
                    'journal_id': point_promotion_forlife_id.account_journal_id.id,
                    'line_ids': move_line_vals,
                    'point_order_type': 'reset_order'
                }
                account_move_obj.create(move_vals).sudo().action_post()

                for partner in reset_forlife_partners:
                    # create reset history point
                    history_point_obj.create({
                        'partner_id': partner.id,
                        'point_order_type': 'reset_order',
                        'store': 'forlife',
                        'create_date': now,
                        'date_order': now,
                        'points_fl_order': -partner.total_points_available_forlife,
                        'points_store': -partner.total_points_available_forlife,
                        'reason': _("Hệ thống chạy tự động")
                    })

                # Update reset date
                new_reset_date = now + relativedelta(days=point_promotion_forlife_id.point_expiration)
                vals.update({
                    'reset_day_of_point_forlife': new_reset_date,
                    'point_forlife_reseted': False
                })

            reset_forlife_partners.write(vals)

        # Reset Format point
        reset_format_partners = self.search([('reset_day_of_point_format', '<=', now), ('point_format_reseted', '=', False)])
        if reset_format_partners:
            # vals = {'point_format_reseted': True}
            vals = {}
            # create journal entries
            if point_promotion_format_id:
                move_line_vals = [(0, 0, {
                    'account_id': point_promotion_format_id.point_customer_id.property_account_receivable_id.id,
                    'partner_id': point_promotion_format_id.point_customer_id.id,
                    'name': partner.name,
                    'debit': partner.total_points_available_format * 1000,
                    'credit': 0
                }) for partner in reset_format_partners]
                move_line_vals += [(0, 0, {
                    'account_id': point_promotion_format_id.acc_accumulate_points_id.id,
                    'debit': 0,
                    'credit': sum(reset_format_partners.mapped('total_points_available_format')) * 1000
                })]
                move_vals = {
                    'ref': 'Format',
                    'date': now.date(),
                    'journal_id': point_promotion_format_id.account_journal_id.id,
                    'line_ids': move_line_vals,
                    'point_order_type': 'reset_order'
                }
                account_move_obj.create(move_vals).sudo().action_post()

                for partner in reset_format_partners:
                    # create reset history point
                    history_point_obj.create({
                        'partner_id': partner.id,
                        'point_order_type': 'reset_order',
                        'store': 'format',
                        'create_date': now,
                        'date_order': now,
                        'points_fl_order': -partner.total_points_available_format,
                        'points_store': -partner.total_points_available_format,
                        'reason': _("Hệ thống chạy tự động")
                    })

                # Update reset date
                new_reset_date = now + relativedelta(days=point_promotion_format_id.point_expiration)
                vals.update({
                    'reset_day_of_point_format': new_reset_date,
                    'point_format_reseted': False
                })

            reset_format_partners.write(vals)
