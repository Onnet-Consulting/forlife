from odoo import api, fields, models


class Voucher(models.Model):
    _name = 'program.voucher.line'
    _description = 'Info of Program Voucher'

    program_voucher_id = fields.Many2one('program.voucher')

    price = fields.Monetary('Price')

    currency_id = fields.Many2one('res.currency', compute='_compute_currency_field')

    partner_ids = fields.Many2many('res.partner', string='Customers')

    count = fields.Integer('Count')

    @api.depends('program_voucher_id.currency_id')
    def _compute_currency_field(self):
        for rec in self:
            rec.currency_id = rec.program_voucher_id.currency_id.id