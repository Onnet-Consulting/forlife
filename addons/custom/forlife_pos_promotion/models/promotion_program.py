# -*- coding: utf-8 -*-
import base64
import itertools
import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.models import NewId
from odoo.osv import expression

REWARD_TYPE = [
        ('combo_amount', 'Combo Discount Amount'),
        ('combo_percent', 'Combo Discount Percent'),
        ('combo_fixed_price', 'Combo Discount Fixed Price'),
        ('combo_discount_percent_x', 'Combo Discount Percent X'),
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
        ('cart_discount_amount', 'Cart Discount Amount'),
        ('cart_get_x_free', 'Cart Get X Free'),
    ]


class PromotionConditionProduct(models.Model):
    _name = 'promotion.condition.product'
    _description = "Promotion Condition Product"
    _rec_name = 'product_product_id'
    _table = 'product_product_promotion_program_rel'

    product_product_id = fields.Many2one('product.product', required=True, index=True, string='Product')
    promotion_program_id = fields.Many2one('promotion.program', required=True, index=True, string='Promotion Program')

    def init(self):
        self.env.cr.execute("""
            ALTER TABLE product_product_promotion_program_rel ADD COLUMN IF NOT EXISTS id SERIAL; """)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._recompute_json_binary_fields()
        return res

    def unlink(self):
        program = self.promotion_program_id
        res = super(PromotionConditionProduct, self).unlink()
        if program:
            program._compute_json_valid_product_ids()
        return res

    def _recompute_json_binary_fields(self):
        programs = self.env['promotion.program'].search([('id', 'in', self.promotion_program_id.ids)])
        programs._compute_json_valid_product_ids()


class PromotionProgram(models.Model):
    _name = 'promotion.program'
    _description = 'Promotion Program'
    _inherit = 'promotion.configuration'
    _order = 'promotion_type, sequence'

    campaign_id = fields.Many2one('promotion.campaign', name='Campaign', ondelete='restrict')

    active = fields.Boolean(default=True)
    name = fields.Char('Program Name', required=True)
    code = fields.Char('Code')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id', readonly=False, required=True, store=True,
        precompute=True)
    currency_symbol = fields.Char(related='currency_id.symbol')

    brand_id = fields.Many2one(related='campaign_id.brand_id', string='Brand', store=True, required=False)
    store_ids = fields.Many2many(related='campaign_id.store_ids', string='Stores')
    from_date = fields.Datetime(related='campaign_id.from_date', string='From Date')
    to_date = fields.Datetime(related='campaign_id.to_date', string='To Date')
    month_ids = fields.Many2many(related='campaign_id.month_ids', string='Months')
    dayofmonth_ids = fields.Many2many(related='campaign_id.dayofmonth_ids', string='DayOfMonth')
    dayofweek_ids = fields.Many2many(related='campaign_id.dayofweek_ids', string='DayOfWeek')
    hour_ids = fields.Many2many(related='campaign_id.hour_ids', string='Hours')

    applicability = fields.Selection([
        ('current', 'Current order'),
        ('future', 'Future orders')], default='current', required=True, readonly=False, store=True)

    discount_apply_on = fields.Selection([
        ('order', 'Order'),
        ('specific_products', 'Specific Products'),
        # ('cheapest_product', 'Cheapest Products'),
    ], string='Discount Apply On', required=True, default='order')

    limit_usage = fields.Boolean(string='Limit Order Usage')
    max_usage = fields.Integer(string='Max Order Number')

    limit_usage_per_order = fields.Boolean(string='Limit usage per Order', help='Based on qty of combo/product')
    max_usage_per_order = fields.Integer(string='Max qty per Order', help='Based on qty of combo/product')

    limit_usage_per_customer = fields.Boolean(string='Limit usage per Customer', help='Based on qty of combo/product')
    max_usage_per_customer = fields.Integer(string='Max qty per Customer', help='Based on qty of combo/product')

    limit_usage_per_program = fields.Boolean(string='Limit usage per Program', help='Based on qty of combo/product')
    max_usage_per_program = fields.Integer(string='Max qty per Program', help='Based on qty of combo/product')

    state = fields.Selection(related='campaign_id.state', store=True, readonly=True)

    promotion_type = fields.Selection([
        ('combo', 'Combo'),
        ('code', 'Code'),
        ('cart', 'Cart'),
        ('pricelist', 'Pricelist'),
    ], string='Program Type')

    pos_config_ids = fields.Many2many(
        related='campaign_id.pos_config_ids', string="Point of Sales", help="Restrict publishing to those shops.",
        readonly=True)

    customer_domain = fields.Char(related='campaign_id.customer_domain', store=True)
    valid_customer_ids = fields.Many2many(related='campaign_id.valid_customer_ids')

    total_order_count = fields.Integer("Total Order Count", compute="_compute_total_order_count")
    order_ids = fields.Many2many('pos.order', compute="_compute_total_order_count")

    # Combo
    combo_line_ids = fields.One2many(
        'promotion.combo.line', 'program_id', 'Conditional rules', copy=True, readonly=False, store=True)
    with_code = fields.Boolean('Use a code', default=False)
    combo_code = fields.Char('Combo Code')
    combo_name = fields.Char('Combo Name')
    qty_per_combo = fields.Float(compute='_compute_qty_per_combo')
    # Code
    discount_based_on = fields.Selection([
        ('unit_price', 'Unit Price'),
        ('discounted_price', 'Discounted Price')], string='Discount Based On', required=True, default='unit_price')
    product_ids = fields.Many2many(
        'product.product', relation='product_product_promotion_program_rel', string='Products',
        domain="[('available_in_pos', '=', True)]")
    product_categ_ids = fields.Many2many('product.category', string='Product Categories')
    product_domain = fields.Char()
    min_quantity = fields.Float('Minimum Quantity', default=1)
    # valid_product_ids = fields.Many2many(
        # 'product.product', compute='_compute_valid_product_ids', string='Valid Products')
    product_count = fields.Integer(compute='_compute_valid_product_ids', string='Valid Product Counts')
    json_valid_product_ids = fields.Binary(
        compute='_compute_json_valid_product_ids', string='Json Valid Products', store=True)

    # Cart
    only_condition_product = fields.Boolean('Only Condition Product?')
    is_original_price = fields.Boolean('Is Price Original?', help='Price of condition product must be original!')
    order_amount_min = fields.Float()
    incl_reward_in_order = fields.Boolean(string='Include Reward in Order')
    incl_reward_in_order_type = fields.Selection([
        ('no_incl', 'No Include'),
        ('unit_price', 'Unit Price'),
        ('discounted_price', 'Discounted Price')
    ], string='Include Reward in Order', compute='_compute_incl_reward_in_order_type', store=True, readonly=False)
    # Pricelist

    pricelist_item_ids = fields.One2many(
        'promotion.pricelist.item', 'program_id', string='Pricelist Item', context={'active_test': False})
    pricelist_item_count = fields.Integer(compute='_compute_pricelist_item_count')

    # Rewards
    progressive_reward_compute = fields.Boolean('Progressive Reward Compute', default=False)
    reward_type = fields.Selection(REWARD_TYPE, string='Reward Type')

    reward_ids = fields.One2many('promotion.reward.line', 'program_id', 'Rewards', copy=True, readonly=False, store=True)
    qty_min_required = fields.Float(compute='_qty_min_required', help='Use for Combo Program  based on quantity of the Combo')

    voucher_program_id = fields.Many2one(
        'program.voucher', domain="[('type', '=', 'e')]", string='Voucher Program')
    voucher_product_id = fields.Many2one(
        'product.template', related='voucher_program_id.product_id', string='Voucher Product Template')
    voucher_product_variant_id = fields.Many2one(
        'product.product', domain="[('product_tmpl_id', '=', voucher_product_id)]", string='Voucher Product Variant')
    voucher_price = fields.Monetary(string='Voucher Price', currency_field='currency_id')
    voucher_apply_product_ids = fields.Many2many(
        'product.product', related='voucher_program_id.product_apply_ids', string='Applicable Products')
    voucher_ids = fields.One2many('voucher.voucher', 'promotion_program_id')
    voucher_count = fields.Integer(compute='_compute_voucher_count')

    code_ids = fields.One2many('promotion.code', 'program_id')
    code_count = fields.Integer(compute='_compute_code_count')

    discount_product_ids = fields.Many2many(
        'product.product', 'promotion_program_discount_product_rel', domain="[('available_in_pos', '=', True)]")
    discount_product_count = fields.Integer(compute='_compute_discount_product_count')
    reward_product_count = fields.Integer(compute='_compute_reward_product_count')
    reward_product_ids = fields.Many2many(
        'product.product', 'promotion_program_reward_product_rel', domain="[('available_in_pos', '=', True)]")
    reward_quantity = fields.Float()

    disc_amount = fields.Float('Discount Amount')
    disc_percent = fields.Float('Discount Percent')
    disc_fixed_price = fields.Float('Fixed Price')
    disc_max_amount = fields.Float('Max Discount Amount')

    show_gen_code = fields.Boolean('Show Gencode button', compute='_show_gen_code')

    registering_tax = fields.Boolean('Register Tax')
    tax_from_date = fields.Date('Registered Tax From')
    tax_to_date = fields.Date('Registered Tax To')

    apply_online = fields.Boolean(string='Apply online', default=False)
    for_new_customer = fields.Boolean(string='For new customer', default=False)

    notification_id = fields.Char('Notification ID', help='Id của thông báo trên trang quản trị app')

    @api.constrains('promotion_type', 'combo_line_ids', 'reward_ids', 'reward_type')
    def _check_duplicate_product_in_combo(self):
        for program in self:
            if program.promotion_type == 'combo' and program.combo_line_ids:
                list_of_set = [set(line.mapped('product_ids.id')) for line in program.combo_line_ids]
                combine_couple_of_set = itertools.combinations(list_of_set, 2)
                for couple in combine_couple_of_set:
                    if couple[0] & couple[1]:
                        raise UserError(_('Products duplication occurs in the combo formula!'))
            if program.promotion_type == 'combo' and not program.combo_line_ids:
                raise UserError(_('%s: Combo Formular is not set!') % program.name)
            if program.promotion_type == 'combo' and program.reward_ids and program.reward_type in ['combo_percent_by_qty', 'combo_fixed_price_by_qty']:
                if len(program.reward_ids) != len(set(program.reward_ids.mapped('quantity_min'))):
                    raise UserError(_('%s: Không được khai báo cùng số lượng trên các chi tiết combo!') % program.name)

    _sql_constraints = [
        ('check_dates', 'CHECK (from_date <= to_date)', 'End date may not be before the starting date.'),
        ('check_dates_tax_register', 'CHECK (tax_from_date <= tax_to_date)', 'End date may not be before the starting date.'),
        ('disc_amount', 'CHECK (disc_amount >= 0.0 )', 'Discount Amount must be positive'),
        ('disc_percent', 'CHECK (disc_percent >= 0 and disc_percent <= 100)', 'Discount Percent must be between 0.0 and 100.0'),
        ('disc_fixed_price', 'CHECK (disc_fixed_price >= 0.0)', 'Discount Fixed Price must be positive'),
        ('disc_max_amount', 'CHECK (disc_max_amount >= 0.0)', 'Max Discount Amount must be positive.'),
        ('max_usage', 'CHECK (max_usage >= 0.0)', 'Max Usage must be positive.')
    ]

    @api.depends('company_id')
    def _compute_currency_id(self):
        for program in self:
            program.currency_id = program.company_id.currency_id or program.currency_id

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

    @api.depends('voucher_ids')
    def _compute_voucher_count(self):
        read_group_data = self.env['voucher.voucher']._read_group([('promotion_program_id', 'in', self.ids)], ['promotion_program_id'], ['promotion_program_id'])
        count_per_program = {r['promotion_program_id'][0]: r['promotion_program_id_count'] for r in read_group_data}
        for program in self:
            program.voucher_count = count_per_program.get(program.id, 0)

    @api.depends('product_ids', 'product_categ_ids')
    def _compute_valid_product_ids(self):
        for line in self:
            product_ids_list = line._get_valid_product_ids()
            line.product_count = len(product_ids_list)

    @api.depends('discount_product_ids')
    def _compute_discount_product_count(self):
        sql = """
        SELECT promotion_program_id, count(product_product_id) FROM promotion_program_discount_product_rel
        WHERE promotion_program_id in %(promotion_programs)s
        GROUP BY promotion_program_id
        """
        self.env.cr.execute(sql, {'promotion_programs': tuple(self.ids)})
        result = {
            promotion_program_id: count
            for promotion_program_id, count in self.env.cr.fetchall()
        }
        for pro in self:
            pro.discount_product_count = result.get(pro.id, 0)

    @api.depends('reward_product_ids')
    def _compute_reward_product_count(self):
        sql = """
        SELECT promotion_program_id, count(product_product_id) FROM promotion_program_reward_product_rel
        WHERE promotion_program_id in %(promotion_programs)s
        GROUP BY promotion_program_id
        """
        self.env.cr.execute(sql, {'promotion_programs': tuple(self.ids)})
        result = {
            promotion_program_id: count
            for promotion_program_id, count in self.env.cr.fetchall()
        }
        for pro in self:
            pro.reward_product_count = result.get(pro.id, 0)

    @api.depends('product_ids', 'product_categ_ids')
    def _compute_json_valid_product_ids(self):
        for pro in self:
            product_ids_list = pro._get_valid_product_ids()
            product_ids_json_encode = base64.b64encode(json.dumps(product_ids_list).encode('utf-8'))
            pro.json_valid_product_ids = product_ids_json_encode

    @api.depends('incl_reward_in_order')
    def _compute_incl_reward_in_order_type(self):
        for pro in self:
            pro.incl_reward_in_order_type = pro.incl_reward_in_order and 'discounted_price' or 'unit_price'

    def _compute_total_order_count(self):
        self.total_order_count = 0
        for program in self:
            usages = self.env['promotion.usage.line'].search([('program_id', '=', program.id)])
            program.total_order_count = len(usages.mapped('order_id'))
            program.order_ids = usages.mapped('order_id')

    def _compute_pricelist_item_count(self):
        for pro in self:
            pro.pricelist_item_count = len(pro.pricelist_item_ids)

    def _compute_qty_per_combo(self):
        for pro in self:
            pro.qty_per_combo = sum(pro.combo_line_ids.mapped('quantity')) or 0.0

    def _qty_min_required(self):
        for program in self:
            program.qty_min_required = 0
            if program.reward_type in ['combo_percent_by_qty', 'combo_fixed_price_by_qty'] and program.reward_ids:
                program.qty_min_required = min(program.reward_ids.mapped('quantity_min')) or 0

    def _get_valid_product_ids(self):
        self.ensure_one()
        sql = "SELECT product_product_id FROM product_product_promotion_program_rel " \
              "WHERE promotion_program_id = %s;" % self.id
        self.env.cr.execute(sql)
        data = self.env.cr.fetchall()
        return list(itertools.chain(*data)) or []

    def _show_gen_code(self):
        for program in self:
            if program.id == NewId:
                program.show_gen_code = False
            elif program.with_code or program.promotion_type == 'code':
                program.show_gen_code = True
            else:
                program.show_gen_code = False

    @api.onchange('tax_from_date', 'tax_to_date')
    def onchange_from_to_date(self):
        if self.tax_from_date and self.tax_to_date and self.tax_from_date > self.tax_to_date:
            raise UserError('Chương trình "%s": Ngày bắt đầu phải nhỏ hơn ngày kết thúc!' % self.name or '')

    @api.onchange('voucher_product_variant_id')
    def onchange_voucher_product(self):
        if self.voucher_product_variant_id:
            self.voucher_price = self.voucher_product_variant_id.price
        else:
            self.voucher_price = 0.0

    @api.onchange('promotion_type', 'reward_type')
    def onchange_promotion_type(self):
        if not self.promotion_type:
            self.reward_type = False
        elif self.promotion_type == 'combo':
            if self.reward_type and not self.reward_type.startswith('combo'):
                self.reward_type = 'combo_amount'
        elif self.promotion_type == 'code':
            self.with_code = True
            self.combo_line_ids = False
            if self.reward_type and not self.reward_type.startswith('code'):
                self.reward_type = 'code_amount'
        elif self.promotion_type == 'cart':
            self.with_code = False
            self.combo_line_ids = False
            if self.reward_type and not self.reward_type.startswith('cart'):
                self.reward_type = 'cart_discount_percent'
        else:
            self.reward_type = False

    @api.onchange('reward_type')
    def onchange_reward_type_change(self):
        if self.reward_type not in ('combo_percent_by_qty', 'combo_fixed_price_by_qty'):
            self.reward_ids = False

    def unlink(self):
        for program in self:
            if bool(self.env['promotion.usage.line'].search([('program_id', '=', program.id)])):
                raise UserError(_('Can not unlink program which is already used!'))
        return super().unlink()

    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % self.name)
        return super().copy(default)

    def action_recompute_new_field_binary(self):
        self.search([])._compute_json_valid_product_ids()
        self.search([]).combo_line_ids._compute_json_valid_product_ids()
        return True

    def open_products(self):
        action = self.env["ir.actions.actions"]._for_xml_id("product.product_normal_action_sell")
        action['domain'] = [('id', 'in', self.product_ids.ids)]
        return action

    def action_open_condition_product(self):
        return {
            'name': _('Condition Products') + (self.name and _(' of %s') % self.name) or '',
            'domain': [('promotion_program_id', '=', self.id)],
            'res_model': 'promotion.condition.product',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': {'default_promotion_program_id': self.id}
        }

    def view_program(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("forlife_pos_promotion.promotion_program_action")
        form_view = [(self.env.ref('forlife_pos_promotion.promotion_program_view_form').id, 'form')]
        action['view_mode'] = 'form'
        action['res_id'] = self.id
        action['views'] = form_view
        action['domain'] = [('id', '=', self.id)]
        return action

    def action_open_promotion_codes(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id("forlife_pos_promotion.promotion_code_card_action")
        action['name'] = _('Promotion Code') + (self.name and _(' of %s') % self.name) or '',
        action['display_name'] = action['name']
        action['context'] = {
            'program_type': self.promotion_type,
            'program_item_name': _('Promotion Code'),
            'default_program_id': self.id,
        }
        action['domain'] = [('program_id', '=', self.id)]
        return action

    def action_open_issued_vouchers(self):
        self.ensure_one()
        return {
            'name': _('Issued Vouchers') + (self.name and _(' of %s') % self.name) or '',
            'domain': [('id', 'in', self.voucher_ids.ids)],
            'res_model': 'voucher.voucher',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }

    def action_open_orders(self):
        self.ensure_one()
        return {
            'name': _('Orders') + (self.name and _(' of %s') % self.name) or '',
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'tree'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.order_ids.ids)],
        }

    def action_open_pricelist_items(self):
        return {
            'name': _('Product Pricelist Items') + (self.name and _(' of %s') % self.name) or '',
            'res_model': 'promotion.pricelist.item',
            'view_mode': 'tree',
            'views': [
                (self.env.ref('forlife_pos_promotion.promotion_pricelist_item_tree_view').id, 'tree'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id, 'search_default_active': 1}
        }

    def action_open_discount_product(self):
        return {
            'name': _('Discount Products') + (self.name and _(' of %s') % self.name) or '',
            'domain': [('promotion_program_id', '=', self.id)],
            'res_model': 'promotion.discount.product',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': {'default_promotion_program_id': self.id}
        }

    def action_open_reward_product(self):
        return {
            'name': _('Reward Products') + (self.name and _(' of %s') % self.name) or '',
            'domain': [('promotion_program_id', '=', self.id)],
            'res_model': 'promotion.reward.product',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': {'default_promotion_program_id': self.id}
        }


class PromotionDiscountProduct(models.Model):
    _name = 'promotion.discount.product'
    _rec_name = 'product_product_id'
    _description = 'Promotion Discount Product'
    _table = 'promotion_program_discount_product_rel'

    product_product_id = fields.Many2one('product.product', required=True, index=True, string='Product')
    promotion_program_id = fields.Many2one('promotion.program', required=True, index=True, string='Promotion Program')

    def init(self):
        self.env.cr.execute("""
            ALTER TABLE promotion_program_discount_product_rel ADD COLUMN IF NOT EXISTS id SERIAL; """)


class PromotionRewardProduct(models.Model):
    _name = 'promotion.reward.product'
    _rec_name = 'product_product_id'
    _description = 'Promotion Reward Product'
    _table = 'promotion_program_reward_product_rel'

    product_product_id = fields.Many2one('product.product', required=True, index=True, string='Product')
    promotion_program_id = fields.Many2one('promotion.program', required=True, index=True, string='Promotion Program')

    def init(self):
        self.env.cr.execute("""
            ALTER TABLE promotion_program_reward_product_rel ADD COLUMN IF NOT EXISTS id SERIAL; """)
