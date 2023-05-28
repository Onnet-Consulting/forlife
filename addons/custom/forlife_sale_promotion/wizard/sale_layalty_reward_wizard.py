# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleLoyaltyRewardWizard(models.TransientModel):
    _inherit = 'sale.loyalty.reward.wizard'

    def action_apply(self):
        res = super(SaleLoyaltyRewardWizard, self).action_apply()
        for line in self.order_id.order_line:
            if line.is_reward_line:
                if line.reward_id.reward_type == "product":
                    line.write({'x_free_good': True, 'price_unit': 0, 'x_cart_discount_fixed_price': 0})
        return res
        # self.selected_reward_id
        # self.ensure_one()
        # if not self.selected_reward_id:
        #     raise ValidationError(_('No reward selected.'))
        # claimable_rewards = self.order_id._get_claimable_rewards()
        # selected_coupon = False
        # for coupon, rewards in claimable_rewards.items():
        #     if self.selected_reward_id in rewards:
        #         selected_coupon = coupon
        #         break
        # if not selected_coupon:
        #     raise ValidationError(_('Coupon not found while trying to add the following reward: %s', self.selected_reward_id.description))
        # self.order_id._apply_program_reward(self.selected_reward_id, coupon, product=self.selected_product_id)
        # self.order_id._update_programs_and_rewards()
        # return True
