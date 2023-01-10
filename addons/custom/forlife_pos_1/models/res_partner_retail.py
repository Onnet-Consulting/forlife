# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerRetail(models.Model):
    _name = 'res.partner.retail'
    _description = 'Partner Retail Type'

    name = fields.Char(string="Name", required=True)
    # FIXME: uncomment below field after merge code from alpha branch
    # brand_id = fields.Many2one('brand', string='Brand', required=True)
    code = fields.Char(string="Code", required=True)
    is_default = fields.Boolean(string='Is default', default=False,
                                help="If new partner don't have any retail type, we will get all retail type with this field set to True")
