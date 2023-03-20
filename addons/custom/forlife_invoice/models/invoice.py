from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Char(string="Invoce Description")
    invoice_reference = fields.Char(string="Invoice Reference")
    currency_rate = fields.Float("Currency Rate")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    description = fields.Char(string="Description")
    type = fields.Selection(related="product_id.detailed_type")
