# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    group_id = fields.Many2one('res.partner.group', string='Group')
    job_ids = fields.Many2many('res.partner.job', string='Jobs')
    customer_type = fields.Selection([('employee', 'Employee'), ('app', 'App member'), ('retail', 'Retail')], string='Customer type')
    birthday = fields.Date(string='Birthday')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    phone = fields.Char(required=True, default='_')
    ref = fields.Char(required=True, default='_', readonly=True)
    barcode = fields.Char(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for value in vals_list:
            group_id = value.get('group_id')
            if group_id:
                partner_group = self.env['res.partner.group'].browse(group_id)
                if partner_group.sequence_id:
                    value['ref'] = partner_group.sequence_id.next_by_id()
                else:
                    value['ref'] = partner_group.code + (value['ref'] or '')
        res = super(ResPartner, self).create(vals_list)
        return res
