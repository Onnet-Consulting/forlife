# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _rec_names_search = ['display_name', 'email', 'ref', 'vat', 'company_registry', 'phone', 'mobile']

    store_fo_ids = fields.One2many('store.first.order', inverse_name='customer_id', string='Store First Order')
