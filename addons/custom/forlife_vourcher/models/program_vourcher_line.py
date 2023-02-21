from odoo import api, fields, models


class Vourcher(models.Model):
    _name = 'program.vourcher.line'
    _description = 'Info of Program Vourcher'

    program_vourcher_id = fields.Many2one('program.vourcher')

    price = fields.Monetary('Price')

    currency_id = fields.Many2one('res.currency')

    partner_ids = fields.Many2many('res.partner', string='Customers')

    count = fields.Integer('Count')