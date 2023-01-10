# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerRetail(models.Model):
    _name = 'res.partner.retail'
    _description = 'Partner Retail Type'

    name = fields.Char(string="Name", required=True)
    brand_id = fields.Many2one('brand', string='Brand', required=True)
    code = fields.Char(string="Code", required=True)
    retail_type = fields.Selection([('employee', 'Employee'), ('app', 'App'), ('customer', 'Customer')], string='Type')

    def name_get(self):
        return [(retail.id, '%s %s' % (retail.name, retail.brand_id.name)) for retail in self]
