from odoo import models, fields, api, _

class PromotionProgram(models.Model):
    _inherit = 'promotion.program'

    is_for_nhanh = fields.Boolean(related='campaign_id.is_for_nhanh', string='CTKM cho nhanh', store=True)
