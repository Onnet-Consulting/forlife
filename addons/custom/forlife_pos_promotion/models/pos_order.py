# -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    cart_promotion_program_id = fields.Many2one('promotion.program', 'Applied Cart Promotion', readonly=True)
    reward_voucher_id = fields.Many2one('voucher.voucher', 'Reward Voucher', readonly=True)

    @api.model
    def _process_order(self, order, draft, existing_order):
        # Kiểm tra đơn hàng có chương trình KM trong thời hạn đăng kí thuế
        date_order = fields.Date.from_string(order['data']['creation_date'].replace('T', ' ')[:19])
        for line in order['data']['lines']:
            for usage in line[2]['promotion_usage_ids']:
                program = self.env['promotion.program'].browse(usage[2].get('program_id'))
                if program.registering_tax and program.tax_from_date <= date_order <= program.tax_to_date:
                    usage[2]['registering_tax'] = True
        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        # Gắn Khách hàng vào code đã sử dụng
        code_ids = []
        partner_id = order['data']['partner_id']
        if partner_id:
            for line in order['data']['lines']:
                code_ids += [usage[2].get('code_id') for usage in line[2]['promotion_usage_ids']]
            if len(code_ids) > 0:
                codes = self.env['promotion.code'].browse(code_ids)
                codes.used_partner_ids |= self.env['res.partner'].browse(partner_id)
        # Kiểm tra và tạo mã Voucher cho khách hàng từ CTKM
        reward_voucher_program_id = order['data'].get('reward_voucher_program_id', 0)
        cart_promotion_program_id = order['data'].get('cart_promotion_program_id', 0)
        if reward_voucher_program_id and cart_promotion_program_id:
            self.issue_promotion_voucher(order_id, reward_voucher_program_id, cart_promotion_program_id)
        return order_id

    def issue_promotion_voucher(self, order_id, reward_voucher_program_id, program_id):
        pos_order = self.env['pos.order'].browse(order_id)
        voucher_program = self.env['program.voucher'].browse(reward_voucher_program_id)
        program = self.env['promotion.program'].browse(program_id)

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
            'orig_pos_order_id': pos_order.id
        })
        pos_order.cart_promotion_program_id = program
        pos_order.reward_voucher_id = voucher
