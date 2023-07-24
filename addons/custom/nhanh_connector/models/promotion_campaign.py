# -*- coding: utf-8 -*-

import time
from odoo import _, models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PromotionCampaign(models.Model):
    _inherit = 'promotion.campaign'

    # tuuh
    is_for_nhanh = fields.Boolean('CTKM cho nhanh')

    def write(self, vals):
        res = super().write(vals)
        if vals.get("state") and vals.get("state") == 'finished':
            self.sync_price_product_to_nhanh_when_close_pc()

        return res

    def start_sync_price_product_to_nhanh(self):
        domain = [
            ('is_for_nhanh', '=', True), 
            ('program_id', '!=', False),
            ('state', '=', 'in_progress'),
            ('to_date', '>=', fields.Datetime.now()),
            ('from_date', '<=', fields.Datetime.now()),
        ]
        pl_res = self.env["promotion.pricelist.item"].sudo().search(domain, order="fixed_price ASC")
        lines = pl_res.filtered(
            lambda r: r.product_tmpl_id.nhanh_id != False 
            and r.product_tmpl_id.categ_id.category_type_id.x_sync_nhanh
            and r.product_tmpl_id.brand_id.id
        )

        if len(lines):
            exits_prod_tmpl = {}
            for line in lines:
                if exits_prod_tmpl.get(line.product_tmpl_id.id):
                    continue
                exits_prod_tmpl[line.product_tmpl_id.id] = line
                line.product_tmpl_id.synchronized_product_exists_nhanh(line, pl_list_price=True)


    def sync_price_product_to_nhanh_when_close_pc(self):
        domain = [
            ('is_for_nhanh', '=', True), 
            ('program_id', '!=', False),
            ('state', '=', 'in_progress'),
            ('to_date', '>=', fields.Datetime.now()),
            ('from_date', '<=', fields.Datetime.now()),
        ]
        pl_res_in_progress = self.env["promotion.pricelist.item"].sudo().search(domain)
        p_tmpl_in_progress = pl_res_in_progress.mapped("product_tmpl_id")

        if p_tmpl_in_progress: 
            pl_res_close = self.env["promotion.pricelist.item"].sudo().search([
                ('campaign_id', 'in', self.ids),
                ('product_tmpl_id', 'nin', p_tmpl_in_progress.ids)
            ])
        else:
            pl_res_close = self.env["promotion.pricelist.item"].sudo().search([
                ('campaign_id', 'in', self.ids)
            ])

        lines = pl_res_close.filtered(
            lambda r: r.product_tmpl_id.nhanh_id != False 
            and r.product_tmpl_id.categ_id.category_type_id.x_sync_nhanh
            and r.product_tmpl_id.brand_id.id
        )
        if len(lines):
            exits_prod_tmpl = {}
            for line in lines:
                if exits_prod_tmpl.get(line.product_tmpl_id.id):
                    continue
                line.product_tmpl_id.synchronized_product_exists_nhanh(line, pl_list_price=False)

