# -*- coding: utf-8 -*-

import time
from odoo import _, models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PromotionCampaign(models.Model):
    _inherit = 'promotion.campaign'

    # tuuh
    is_for_nhanh = fields.Boolean('CTKM cho nhanh')

    def start_sync_update_price_product_to_nhanh(self):
        # get all promotion_campaign:
        nhanh_promotion_ids = self.env['promotion.campaign'].sudo().search(
            [('from_date', '<=', fields.Date.today()), ('to_date', '<=', fields.Date.today()),
             ('state', '=', 'in_progress')])
        pricelist_item_ids = nhanh_promotion_ids.mapped('program_ids').filtered(
            lambda p: p.promotion_type == 'pricelist').mapped('pricelist_item_ids')
        for item_id in pricelist_item_ids:
            item_id.product_id.write({
                'list_price': item_id.fixed_price
            })
            time.sleep(3)
