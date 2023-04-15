# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime

VN_COMPANY_CODES = [
    '1200'
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(selection_add=[('vietin', 'Vietin Bank')], default='vietin')

    @api.depends('country_id')
    def _compute_currency_provider(self):
        super()._compute_currency_provider()
        for record in self:
            record.currency_provider = 'vietin'

    # FIXME: add real API here
    def _parse_vietin_data(self):
        rates_dict = {}
        rates_dict['VND'] = (1.0, fields.Date.context_today(self))
        return rates_dict

    @api.model
    def _update_vn_company_currency_provider(self):
        self.env['ir.config_parameter'].sudo().set_param('currency_rate_live.currency_provider', 'vietin')
        companies = self.env['res.company'].search([('code', 'in', VN_COMPANY_CODES)])
        companies.write({'currency_interval_unit': 'daily', 'currency_provider': 'vietin'})
        return True
