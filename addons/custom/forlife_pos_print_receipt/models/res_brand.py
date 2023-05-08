# -*- coding:utf-8 -*-


from odoo import api, fields, models, _


class ResBrand(models.Model):
    _inherit = 'res.brand'

    pos_receipt_footer = fields.Html(string='Receipt Footer', sanitize=False)
