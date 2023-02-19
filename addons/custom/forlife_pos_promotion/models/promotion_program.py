# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression

REWARD_TYPE = [
        ('combo_amount', 'Combo Discount Amount'),
        ('combo_percent', 'Combo Discount Percent'),
        ('combo_fixed_price', 'Combo Discount Fixed Price'),
        ('combo_percent_by_qty', 'Combo Discount Percent by Qty'),
        ('combo_fixed_price_by_qty', 'Combo Discount Fixed Price by Qty'),
        ('code_amount', 'Code Discount Amount'),
        ('code_percent', 'Code Discount Percent'),
        ('code_fixed_price', 'Code Discount Fixed Price'),
        ('code_buy_x_get_y', 'Code Buy X get Y'),
        ('code_buy_x_get_cheapest', 'Code Buy X Get The Cheapest'),
        ('cart_get_voucher', 'Cart Get Voucher'),
        ('cart_discount_percent', 'Cart Discount Percent'),
        ('cart_discount_fixed_price', 'Cart Discount Fixed Price'),
        ('cart_get_x_free', 'Cart Get X Free'),
    ]


class PromotionProgram(models.Model):
    _name = 'promotion.program'
    _description = 'Promotion Program'

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    name = fields.Char('Program Name', required=True)
    code = fields.Char('Code')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id', readonly=False, required=True, store=True,
        precompute=True)
    currency_symbol = fields.Char(related='currency_id.symbol')

    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    store_ids = fields.Many2many('store', string='Stores', required=True)
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    month_ids = fields.Many2many('month.data', string='Months')
    dayofmonth_ids = fields.Many2many('dayofmonth.data', string='DayOfMonth')
    dayofweek_ids = fields.Many2many('dayofweek.data', string='DayOfWeek')
    hour_ids = fields.Many2many('hour.data', string='Hours')

    applicability = fields.Selection([
        ('current', 'Current order'),
        ('future', 'Future orders')], default='current', required=True, readonly=False, store=True)

    discount_apply_on = fields.Selection([
        ('order', 'Order'),
        ('specific_products', 'Specific Products'),
        # ('cheapest_product', 'Cheapest Products'),
    ], string='Discount Apply On', required=True, default='order')

    limit_usage = fields.Boolean(string='Limit Usage')
    max_usage = fields.Integer()

    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished')),
        ('canceled', _('Canceled'))], string='State', default='new')

    promotion_type = fields.Selection([
        ('combo', 'Combo'),
        ('code', 'Code'),
        ('cart', 'Cart'),
        ('pricelist', 'Pricelist'),
    ], string='Program Type')

    pos_config_ids = fields.Many2many(
        'pos.config', readonly=False, string="Point of Sales", help="Restrict publishing to those shops.")

    customer_domain = fields.Char('Customer Domain', default='[]')
    total_order_count = fields.Integer("Total Order Count", compute="_compute_total_order_count")


    # Combo
    combo_line_ids = fields.One2many(
        'promotion.combo.line', 'program_id', 'Conditional rules', copy=True, readonly=False, store=True)
    with_code = fields.Boolean('Use a code', default=True)
    combo_code = fields.Char('Combo Code')
    combo_name = fields.Char('Combo Name')
    apply_multi_program = fields.Boolean()
    # Code
    discount_based_on = fields.Selection([
        ('unit_price', 'Unit Price'),
        ('discounted_price', 'Discounted Price')], string='Discount Based On', required=True, default='unit_price')
    product_ids = fields.Many2many('product.product', string='Products')
    product_categ_ids = fields.Many2many('product.category', string='Product Categories')
    product_domain = fields.Char()
    min_quantity = fields.Float('Minimum Quantity', default=1)
    valid_product_ids = fields.Many2many(
        'product.product', compute='_compute_valid_product_ids', string='Valid Products')
    product_count = fields.Integer(compute='_compute_valid_product_ids', string='Valid Product Counts')

    # Cart
    order_amount_min = fields.Float()
    # Pricelist

    # Rewards
    reward_type = fields.Selection(REWARD_TYPE, string='Reward Type')

    reward_ids = fields.One2many('promotion.reward.line', 'program_id', 'Rewards', copy=True, readonly=False, store=True)

    voucher_ids = fields.One2many('promotion.voucher', 'program_id')

    code_ids = fields.One2many('promotion.code', 'program_id')
    code_count = fields.Integer(compute='_compute_code_count')

    reward_for_referring = fields.Boolean('Rewards for Referring', copy=False, readonly=False)

    discount_product_ids = fields.Many2many('product.product', 'promotion_program_discount_product_rel')
    reward_product_ids = fields.Many2many('product.product', 'promotion_program_reward_product_rel')
    reward_quantity = fields.Float()

    disc_amount = fields.Float('Discount Amount')
    disc_percent = fields.Float('Discount Percent')
    disc_fixed_price = fields.Float('Fixed Price')
    disc_max_amount = fields.Float('Max Discount Amount')

    @api.constrains('combo_line_ids')
    def _check_duplicate_product_in_combo(self):
        for program in self:
            if program.promotion_type == 'combo' and program.combo_line_ids:
                list_of_set = [set(line.mapped('valid_product_ids.id')) for line in program.combo_line_ids]
                combine_couple_of_set = itertools.combinations(list_of_set, 2)
                for couple in combine_couple_of_set:
                    if couple[0] & couple[1]:
                        raise UserError(_('Products duplication occurs in the combo formula!'))

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
    ]

    @api.depends('company_id')
    def _compute_currency_id(self):
        for program in self:
            program.currency_id = program.company_id.currency_id or program.currency_id

    @api.onchange('from_date', 'to_date')
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

    def _get_valid_product_domain(self):
        self.ensure_one()
        domain = []
        if self.product_ids:
            domain = [('id', 'in', self.product_ids.ids)]
        if self.product_categ_ids:
            for categ in self.product_categ_ids:
                if not isinstance(categ.id, NewId):
                    domain = expression.OR([domain, [('categ_id', 'child_of', categ.id)]])
        return domain

    @api.depends('code_ids')
    def _compute_code_count(self):
        read_group_data = self.env['promotion.code']._read_group([('program_id', 'in', self.ids)], ['program_id'], ['program_id'])
        count_per_program = {r['program_id'][0]: r['program_id_count'] for r in read_group_data}
        for program in self:
            program.code_count = count_per_program.get(program.id, 0)

    @api.depends('product_ids', 'product_categ_ids')
    def _compute_valid_product_ids(self):
        for line in self:
            if line.product_ids or line.product_categ_ids:
                domain = line._get_valid_product_domain()
                domain = expression.AND([[('available_in_pos', '=', True)], domain])
                line.valid_product_ids = self.env['product.product'].search(domain)
            else:
                line.valid_product_ids = self.env['product.product']
            line.product_count = len(line.valid_product_ids)

    def _compute_total_order_count(self):
        self.total_order_count = 0
        for program in self:
            program.total_order_count = sum(program.code_ids.mapped('use_count'))

    def open_products(self):
        action = self.env["ir.actions.actions"]._for_xml_id("product.product_normal_action_sell")
        action['domain'] = [('id', 'in', self.valid_product_ids.ids)]
        return action

    def action_open_promotion_codes(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id("forlife_pos_promotion.promotion_code_card_action")
        action['name'] = _('Promotion Code')
        action['display_name'] = action['name']
        action['context'] = {
            'program_type': self.promotion_type,
            'program_item_name': _('Promotion Code'),
            'default_program_id': self.id,
        }
        return action
