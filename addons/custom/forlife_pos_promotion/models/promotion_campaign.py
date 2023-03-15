# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression
from odoo.tools.convert import safe_eval


class PromotionConfiguration(models.AbstractModel):
    _name = 'promotion.configuration'

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_ids = fields.Many2many('store', string='Stores', required=True, domain="[('brand_id','=',brand_id)]")
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    month_ids = fields.Many2many('month.data', string='Months')
    dayofmonth_ids = fields.Many2many('dayofmonth.data', string='DayOfMonth')
    dayofweek_ids = fields.Many2many('dayofweek.data', string='DayOfWeek')
    hour_ids = fields.Many2many('hour.data', string='Hours')

    customer_domain = fields.Char('Customer Domain', default='[]')
    valid_customer_ids = fields.Many2many('res.partner', compute='_compute_valid_customer_ids')

    def _get_partners(self):
        self.ensure_one()
        domain = safe_eval(self.customer_domain or "[('id', '=', 0)]")
        return self.env['res.partner'].search(domain)

    def _compute_valid_customer_ids(self):
        for record in self:
            record.valid_customer_ids = record._get_partners()

    # @api.onchange('from_date', 'to_date')
    def onchange_program_date(self):
        def next_month(m):
            return m < 12 and m + 1 or 1

        def next_day(d):
            return d < 31 and d + 1 or 1
        self.month_ids = False
        self.dayofmonth_ids = False
        if self.from_date and self.to_date:
            if not self.from_date <= self.to_date:
                raise UserError('End date may not be before the starting date.')
            current_month = self.from_date.month
            months = {current_month, self.to_date.month}
            number_of_months = int((self.to_date - self.from_date).days/30)
            if number_of_months >= 1:
                for i in range(number_of_months):
                    months.add(next_month(current_month))
                    current_month += 1
                    if i > 12: break

            current_day = self.from_date.day
            days = {current_day, self.to_date.day}
            number_of_days = int((self.to_date - self.from_date).days)
            if number_of_days >= 1:
                for i in range(number_of_days):
                    days.add(next_day(current_day))
                    current_day += 1
                    if i > 31: break

            self.month_ids = self.env['month.data'].browse(
                [self.env.ref('forlife_promotion.month%s' % m).id for m in months])
            self.dayofmonth_ids = self.env['dayofmonth.data'].browse(
                [self.env.ref('forlife_promotion.dayofmonth%s' % d).id for d in days])


class PromotionCampaign(models.Model):
    _name = 'promotion.campaign'
    _inherit = 'promotion.configuration'
    _description = 'Promotion Campaign'

    name = fields.Char('Campaign')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    pos_config_ids = fields.Many2many(
        'pos.config', readonly=False, string="Point of Sales", help="Restrict publishing to those shops.")

    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished')),
        ('canceled', _('Canceled'))], string='State', default='new')

    program_ids = fields.One2many(
        'promotion.program', 'campaign_id', context={'active_test': False})
    program_count = fields.Integer(compute='_compute_program_count')

    combo_program_ids = fields.One2many('promotion.program', 'campaign_id', domain=[('promotion_type', '=', 'combo')])
    code_program_ids = fields.One2many('promotion.program', 'campaign_id', domain=[('promotion_type', '=', 'code')])
    cart_program_ids = fields.One2many('promotion.program', 'campaign_id', domain=[('promotion_type', '=', 'cart')])
    pricelist_program_ids = fields.One2many('promotion.program', 'campaign_id', domain=[('promotion_type', '=', 'pricelist')])

    has_combo = fields.Boolean(compute='_compute_programs')
    has_code = fields.Boolean(compute='_compute_programs')
    has_cart = fields.Boolean(compute='_compute_programs')
    has_pricelist = fields.Boolean(compute='_compute_programs')

    @api.constrains('program_ids')
    def check_program(self):
        for campaign in self:
            if any([program.promotion_type == 'combo' and not program.combo_line_ids for program in campaign.program_ids]):
                raise UserError(_('Combo\'s Formular must be set for the program!'))

    def _compute_programs(self):
        for campaign in self:
            campaign.has_combo = len(campaign.combo_program_ids)
            campaign.has_code = len(campaign.code_program_ids)
            campaign.has_cart = len(campaign.cart_program_ids)
            campaign.has_pricelist = len(campaign.pricelist_program_ids)

    def _compute_program_count(self):
        for campaign in self:
            campaign.program_count = len(campaign.program_ids)

    def action_open_programs(self):
        action = self.env["ir.actions.actions"]._for_xml_id("forlife_pos_promotion.promotion_program_action")
        action['domain'] = [('id', 'in', self.program_ids.ids)]
        action['context'] = {
            'default_campaign_id': self.id,
        }
        return action

