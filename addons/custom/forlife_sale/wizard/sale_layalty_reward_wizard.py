# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleLoyaltyRewardWizard(models.TransientModel):
    _inherit = 'sale.loyalty.reward.wizard'

    def action_apply(self):
        res = super(SaleLoyaltyRewardWizard, self).action_apply()
        for line in self.order_id.order_line:
            if not line.x_location_id and line.product_id.detailed_type == 'product':
                line.x_location_id = self.order_id.warehouse_id.lot_stock_id if self.order_id.warehouse_id else None
        return res
