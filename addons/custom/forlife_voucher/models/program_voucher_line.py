from odoo import api, fields, models


class Voucher(models.Model):
    _name = 'program.voucher.line'
    _description = 'Info of Program Voucher'

    program_voucher_id = fields.Many2one('program.voucher')

    price = fields.Monetary('Price')

    currency_id = fields.Many2one('res.currency')

    partner_ids = fields.Many2many('res.partner', string='Customers')

    count = fields.Integer('Count')