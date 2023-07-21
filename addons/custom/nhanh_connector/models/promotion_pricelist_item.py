# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, tools



class PromotionPricelistItem(models.Model):
    _inherit = 'promotion.pricelist.item'

    is_for_nhanh = fields.Boolean(related='program_id.is_for_nhanh', string='CTKM cho nhanh', store=False)
    state = fields.Selection(related='program_id.state', string='Campaign State', store=False)
    to_date = fields.Datetime(related='program_id.to_date', string='To Date', store=False)
    from_date = fields.Datetime(related='program_id.from_date', string='From Date',  store=False)

    campaign_id = fields.Many2one('promotion.campaign', name='Campaign', related='program_id.campaign_id', store=False)

    barcode = fields.Char(related='product_id.barcode')
    product_tmpl_id = fields.Many2one('product.template', 
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=False
    )
