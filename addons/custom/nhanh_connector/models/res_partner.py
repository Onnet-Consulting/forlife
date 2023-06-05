# -*- coding: utf-8 -*-

from odoo import _, models, fields, api


class CustomerNhanh(models.Model):
    _inherit = 'res.partner'

    customer_nhanh_id = fields.Integer(string="Id khách hàng bên Nhanh.vn")
    source_record = fields.Boolean(string="From nhanh", default=False)
    type_customer = fields.Selection([
        ('retail_customers', 'Retail customers'),
        ('wholesalers', 'Wholesalers'),
        ('agents', 'Agents')
    ], tracking=True)
    code_current_customers = fields.Char()