# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_info_company_name = fields.Char('Invoice Info Company Name', tracking=True)
    invoice_info_address = fields.Char('Invoice Info Address', tracking=True)
    invoice_info_tax_number = fields.Char('Invoice Info VAT', tracking=True)
