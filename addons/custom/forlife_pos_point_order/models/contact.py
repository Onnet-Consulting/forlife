from odoo import api, fields, models
import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    is_purchased = fields.Boolean('Is Purchased', compute='_compute_is_purchased', store=True)
    is_member_app_forlife = fields.Boolean('Is Member App?', compute='_compute_member_pos')
    is_member_app_format = fields.Boolean('Is Member App?', compute='_compute_member_pos')
    reset_day_of_point_forlife = fields.Datetime('Day Reset Forlife')
    reset_day_of_point_format = fields.Datetime('Day Reset Format')
    total_points_available_forlife = fields.Integer('Total Points Availible', compute='compute_point_total')
    total_points_available_format = fields.Integer('Total Points Availible', compute='compute_point_total')
    history_points_format_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=','format')], readonly=True)
    history_points_forlife_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=','forlife')], readonly=True)

    @api.depends('history_points_format_ids', 'history_points_forlife_ids')
    def compute_point_total(self):
        for rec in self:
            rec.total_points_available_forlife = sum([x.points_store for x in rec.history_points_forlife_ids])
            rec.total_points_available_format = sum([x.points_store for x in rec.history_points_format_ids])


    def _compute_is_purchased(self):
        for rec in self:
            partner_exits = self.env['pos.order'].sudo().search([('partner_id', '=', rec.id)], limit=1)
            if partner_exits:
                rec.is_purchased = True
            else:
                rec.is_purchased = False

    def _compute_member_pos(self):
        for rec in self:
            if rec.group_id and rec.group_id.id == self.env.ref('forlife_pos_app_member.partner_group_c', raise_if_not_found=False).id:
                if self.env.ref('forlife_pos_app_member.res_partner_retail_tokyolife_app',raise_if_not_found=False).id in rec.retail_type_ids.ids:
                    rec.is_member_app_forlife = True
                if self.env.ref('forlife_pos_app_member.res_partner_retail_format_app',raise_if_not_found=False).id in rec.retail_type_ids.ids:
                    rec.is_member_app_format = True
            else:
                rec.is_member_app_forlife = False
                rec.is_member_app_format = False

    def _compute_reset_day(self, date_order, day_expiration, branch):
        if branch == 'forlife':
            self.reset_day_of_point_forlife = date_order + datetime.timedelta(days=day_expiration)
        if branch == 'format':
            self.reset_day_of_point_format = date_order + datetime.timedelta(days=day_expiration)
        return True




