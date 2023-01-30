from odoo import api, fields, models
import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    is_purchased = fields.Boolean('Is Purchased', compute='_compute_is_purchased', store=False)
    is_member_app_forlife = fields.Boolean('Is Member App?', compute='_compute_member_pos', store=True)
    is_member_app_format = fields.Boolean('Is Member App?', compute='_compute_member_pos', store=True)
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
            partner_exits = self.env['pos.order'].sudo().search([('partner_id', '=', rec.id)])
            if len(partner_exits) == 1:
                rec.is_purchased = False
            else:
                rec.is_purchased = True

    @api.depends('group_id','retail_type_ids')
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
        timedelta_in_days = datetime.timedelta(days=day_expiration)
        if branch == 'forlife':
            if (self.reset_day_of_point_forlife and date_order + timedelta_in_days > self.reset_day_of_point_forlife) \
                    or not self.reset_day_of_point_forlife:
                self.reset_day_of_point_forlife = date_order + timedelta_in_days
        if branch == 'format':
            if (self.reset_day_of_point_format and date_order + timedelta_in_days > self.self.reset_day_of_point_format)\
                    or not self.reset_day_of_point_format:
                self.reset_day_of_point_format = date_order + timedelta_in_days
        return True




