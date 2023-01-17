from odoo import api, fields, models
import datetime


class Contact(models.Model):
    _inherit = 'res.partner'

    is_purchased = fields.Boolean('Is Purchased', compute='_compute_is_purchased', store=True)
    reset_day_of_point_forlife = fields.Datetime('Day Reset Forlife')
    reset_day_of_point_format = fields.Datetime('Day Reset Format')
    total_points_available_forlife = fields.Integer('Total Points Availible', compute='compute_point_total')
    total_points_available_format = fields.Integer('Total Points Availible', compute='compute_point_total')
    history_points_format_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=','format')])
    history_points_forlife_ids = fields.One2many('partner.history.point', 'partner_id', string='History Point Store', domain=[('store', '=','forlife')])

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

    # def write(self, values):
    #     for rec in self:
    #         values['reset_day_of_point_forlife'] = rec.reset_day_of_point_forlife + datetime.timedelta(minutes=5)
    #     return super(Contact, self).write(values)

    def _compute_reset_day(self, date_order, day_expiration, branch):
        if branch == 'forlife':
            self.reset_day_of_point_forlife = date_order + datetime.timedelta(days=day_expiration)
        if branch == 'format':
            self.reset_day_of_point_format = date_order + datetime.timedelta(days=day_expiration)
        return True




