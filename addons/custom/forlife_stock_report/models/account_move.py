from odoo import fields, api, models


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    end_period_entry = fields.Boolean(string='Bút toán cuối kỳ', default=False)
    is_change_price = fields.Boolean(string='Bút toán điều chỉnh giá vốn', default=False)