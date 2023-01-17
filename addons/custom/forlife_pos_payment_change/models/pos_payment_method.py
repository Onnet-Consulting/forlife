from odoo import _, fields, models, api


class PosConfigr(models.Model):
    _inherit = "pos.payment.method"

    is_voucher = fields.Boolean('Is Voucher?', default=False)
