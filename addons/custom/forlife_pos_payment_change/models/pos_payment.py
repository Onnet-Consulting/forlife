from odoo import _, fields, models, api


class PosConfigr(models.Model):
    _inherit = "pos.payment"

    payment_name = fields.Char(related='payment_method_id.name')
    is_voucher = fields.Boolean(related='payment_method_id.is_voucher')
