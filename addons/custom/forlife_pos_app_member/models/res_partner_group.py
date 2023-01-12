# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerGroup(models.Model):
    _name = 'res.partner.group'
    _description = 'Partner Group'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    partner_type = fields.Selection([('customer', 'Customer'), ('vendor', 'Vendor'), ('internal', 'Internal')],
                                    string='Type', default='customer', required=True)
    auto_generate = fields.Boolean(string='Auto Generate Code', default=True,
                                   help="If true, we'll generate partner's reference by group's sequence field.\n "
                                        "Otherwise, use group's code to add prefix to partner's reference", required=True)
    sequence_id = fields.Many2one('ir.sequence', string='Sequence')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Group code already exists!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for value in vals_list:
            auto_generate = value.get('auto_generate')
            code = value.get('code')
            if auto_generate:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': value.get('name'),
                    'prefix': code,
                    'padding': 10 - len(code),
                    'company_id': False
                })
                value.update({'sequence_id': sequence.id})
        res = super(ResPartnerGroup, self).create(vals_list)
        return res
