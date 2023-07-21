# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleLoyaltyRewardWizard(models.TransientModel):
    _inherit = 'sale.loyalty.reward.wizard'

    def action_apply(self):
        res = super(SaleLoyaltyRewardWizard, self).action_apply()
        for line in self.order_id.order_line:
            # áp dụng khuyên mãi cho đơn hàng
            if line.is_reward_line:
                if line.reward_id.reward_type == "product":
                    line.write({'x_free_good': True, 'price_unit': 0, 'odoo_price_unit': 0, 'x_cart_discount_fixed_price': 0})
        return res
