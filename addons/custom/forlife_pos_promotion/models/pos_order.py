# -*- coding: utf-8 -*-
import itertools

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    cart_promotion_program_id = fields.Many2one('promotion.program', 'Applied Cart Promotion', readonly=True)
    reward_voucher_id = fields.Many2one('voucher.voucher', 'Reward Voucher', readonly=True)
    ref_reward_code_ids = fields.One2many('promotion.code', 'original_order_id', readonly=True)
    cart_promotion_program_ids = fields.Many2many(
        'promotion.program',
        'pos_order_applied_cart_promotion_program_rel',
        'pos_order_id',
        'cart_program_id',
        'Applied Cart Promotion'
    )
    reward_voucher_ids = fields.Many2many(
        'voucher.voucher',
        'pos_order_voucher_voucher_reward_rel',
        'pos_order_id',
        'voucher_id',
        'Reward Vouchers'
    )

    @api.model
    def _process_order(self, order, draft, existing_order):
        # Kiểm tra đơn hàng có chương trình KM trong thời hạn đăng kí thuế
        date_order = fields.Date.from_string(order['data']['creation_date'].replace('T', ' ')[:19])
        for line in order['data']['lines']:
            for usage in line[2]['promotion_usage_ids']:
                program = self.env['promotion.program'].browse(usage[2].get('program_id'))
                if program.registering_tax and program.tax_from_date <= date_order <= program.tax_to_date:
                    usage[2]['registering_tax'] = True

        # Kiểm tra và ghi nhận số tiền được khuyến mãi vào bảng "pos.order.line.discount.details"
        for line in order['data']['lines']:
            discounted_amount = 0.0
            lst_price = line[2]['price_unit']
            for usage in line[2]['promotion_usage_ids']:
                discount_per_unit = usage[2].get('discount_amount', 0) or 0.0
                if discount_per_unit > 0:
                    discounted_amount += discount_per_unit*line[2]['qty']
                    lst_price = usage[2]['original_price'] > lst_price and usage[2]['original_price'] or lst_price
            if discounted_amount > 0:
                line[2]['discount_details_lines'] = [(0, 0, {
                    'type': 'ctkm',
                    'listed_price': lst_price,
                    'recipe': discounted_amount,
                    'discounted_amount': discounted_amount
                })]

        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        # Gắn Khách hàng vào code đã sử dụng
        code_ids = []
        partner_id = order['data']['partner_id']
        partner = self.env['res.partner'].browse(partner_id)
        if partner.exists():
            for line in order['data']['lines']:
                code_ids += [usage[2].get('code_id') for usage in line[2]['promotion_usage_ids']]
            if len(code_ids) > 0:
                codes = self.env['promotion.code'].sudo().browse(code_ids)
                codes.used_partner_ids |= partner
        # Kiểm tra và tạo mã Voucher cho khách hàng từ CTKM
        cart_promotion_reward_voucher = order['data'].get('cart_promotion_reward_voucher', [])
        if cart_promotion_reward_voucher:
            self.issue_promotion_voucher(order_id, cart_promotion_reward_voucher)
        # Kiểm tra và tạo Mã KM cho CT giới thiệu

        if order['data'].get('reward_for_referring', 0) and order['data'].get('referred_code_id', {}):
            code_data = order['data'].get('referred_code_id', {})
            code = self.env['promotion.code'].sudo().browse(code_data['id'])
            referring_partner_id = code.partner_id
            reward_program = self.env['promotion.program'].browse(code_data.get('reward_program_id', 0))

            gen_code_wizard = self.env['promotion.generate.code'].create({
                'program_id': reward_program.id,
                'max_usage': reward_program.max_usage
            })
            code_create_vals = [gen_code_wizard._get_coupon_values(customer, force_partner=True)
                                for customer in [referring_partner_id, partner]]
            new_codes = self.env['promotion.code'].sudo().create(code_create_vals)
            new_codes.write({
                'original_program_id': code.program_id.id,
                'original_order_id': order_id,
                'original_code_id': code.id
            })

        # Kiểm tra và tạo Mã KM cho chương trình Quà tặng bất ngờ
        if order['data'].get('surprise_reward_program_id', 0) and partner.exists():
            surprise_reward_program_id = order['data'].get('surprise_reward_program_id', 0)
            surprising_reward_line_id = order['data'].get('surprising_reward_line_id', 0)
            surprise_program = self.env['promotion.program'].browse(surprise_reward_program_id)
            if surprise_program:
                gen_code_wizard = self.env['promotion.generate.code'].create({
                    'program_id': surprise_program.id,
                    'max_usage': surprise_program.max_usage
                })
                new_code = self.env['promotion.code'].sudo().create(gen_code_wizard._get_coupon_values(partner, force_partner=True))
                new_code.original_order_id = order_id
                new_code.surprising_reward_line_id = surprising_reward_line_id
        # Kiểm tra và tạo Mã KM cho chương trình mua Voucher tặng code giảm giá
        if order['data'].get('buy_voucher_get_code_rewards', []) and partner.exists():
            for reward in order['data'].get('buy_voucher_get_code_rewards', []):
                code_program_id = reward.get('buy_voucher_reward_program_id', 0)
                line_id = reward.get('surprising_reward_line_id', 0)
                code_program = self.env['promotion.program'].browse(code_program_id)
                if code_program.exists():
                    gen_code_wizard = self.env['promotion.generate.code'].sudo().create({
                        'program_id': code_program.id,
                        'max_usage': code_program.max_usage
                    })
                    new_code = self.env['promotion.code'].sudo().create(gen_code_wizard._get_coupon_values(partner, force_partner=True))
                    new_code.original_order_id = order_id
                    new_code.surprising_reward_line_id = line_id

        # Kiểm tra và ghi nhận số tiền đã sử dụng cho CTKM Code giảm tiền
        code_vals = {}
        for line in order['data']['lines']:
            for usage in line[2]['promotion_usage_ids']:
                code_id = usage[2]['code_id']
                if code_id and usage[2].get('discount_amount', 0):
                    if code_id in code_vals:
                        code_vals[code_id] += line[2]['qty'] * usage[2]['discount_amount']
                    else:
                        code_vals[code_id] = line[2]['qty'] * usage[2]['discount_amount']
        if code_vals:
            get_code = self.env['promotion.code'].sudo().browse
            for [code_id, consumed_amount] in code_vals.items():
                code_obj = get_code(code_id)
                if code_obj.exists() and code_obj.program_id.reward_type == 'code_amount':
                    code_obj.consumed_amount += consumed_amount
        return order_id

    def issue_promotion_voucher(self, order_id, cart_promotion_reward_voucher):
        pos_order = self.env['pos.order'].browse(order_id)
        VoucherProgram = self.env['program.voucher'].sudo()
        Program = self.env['promotion.program'].sudo()
        vouchers = self.env['voucher.voucher']
        programs = Program
        for program_id, reward_voucher_program_id in cart_promotion_reward_voucher:
            voucher_program = VoucherProgram.browse(reward_voucher_program_id)
            program = Program.browse(program_id)
            if not voucher_program.exists() or not voucher_program.exists():
                continue
            voucher = self.env['voucher.voucher'].sudo().create({
                'program_voucher_id': voucher_program.id,
                'type': voucher_program.type,
                'brand_id': voucher_program.brand_id.id,
                'store_ids': [(6, False, voucher_program.store_ids.ids)],
                'start_date': voucher_program.start_date,
                'state': 'sold',
                'partner_id': pos_order.partner_id.id,
                'price': program.voucher_price,
                'price_used': 0,
                'price_residual': program.voucher_price - 0,
                'derpartment_id': voucher_program.derpartment_id.id,
                'end_date': voucher_program.end_date,
                'apply_many_times': voucher_program.apply_many_times,
                'apply_contemp_time': voucher_program.apply_contemp_time,
                'product_voucher_id': voucher_program.product_id.id,
                'purpose_id': voucher_program.purpose_id.id,
                'product_apply_ids': [(6, False, voucher_program.product_apply_ids.ids)],
                'is_full_price_applies': voucher_program.is_full_price_applies,
                'promotion_program_id': program.id,
                'orig_pos_order_id': pos_order.id,
                'notification_id': voucher_program.product_id.get_notification_id(program.voucher_price),
            })
            pos_order.cart_promotion_program_id = program
            pos_order.reward_voucher_id = voucher
            vouchers |= voucher
            programs |= program

        pos_order.reward_voucher_ids = vouchers
        pos_order.cart_promotion_program_ids = programs

    def migrate_voucher_program_many2one_to_many2many(self):
        check_orders = self.search_read([
            ('cart_promotion_program_id', '!=', False),
            ('reward_voucher_id', '!=', False)], fields=['id', 'cart_promotion_program_id', 'reward_voucher_id'])
        check_order_ids_list = [order['id'] for order in check_orders]
        self.env.cr.execute("""
        select pos_order_id from pos_order_applied_cart_promotion_program_rel
        where pos_order_id in %(ids)s""", {'ids': tuple(check_order_ids_list)})
        order_ids_updated = list(set(itertools.chain(*self.env.cr.fetchall())))
        insert_program_vals = [(order['id'], order['cart_promotion_program_id'][0])
                               for order in check_orders if order['id'] not in order_ids_updated]
        insert_voucher_vals = [(order['id'], order['reward_voucher_id'][0])
                               for order in check_orders if order['id'] not in order_ids_updated]
        program_query = """
        INSERT INTO pos_order_applied_cart_promotion_program_rel (pos_order_id, cart_program_id) 
        VALUES {} ON CONFLICT DO NOTHING""".format(", ".join(["%s"] * len(insert_program_vals)))
        self.env.cr.execute(program_query, insert_program_vals)
        voucher_query = """
        INSERT INTO pos_order_voucher_voucher_reward_rel (pos_order_id, voucher_id) 
        VALUES {} ON CONFLICT DO NOTHING""".format(", ".join(["%s"] * len(insert_voucher_vals)))
        self.env.cr.execute(voucher_query, insert_voucher_vals)
