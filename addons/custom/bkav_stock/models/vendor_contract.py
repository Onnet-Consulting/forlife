# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorContract(models.Model):
    _name = 'vendor.contract'
    _description = 'Vendor contract management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_code(self):
        month = date.today().month
        year = date.today().year
        prefix = f'HDNCC{year % 100}{month:02d}/'
        contract_id = self.env['vendor.contract'].search(
            [('company_id', '=', self.env.company.id),
             ('name', 'ilike', prefix)],
            order='name desc',
            limit=1)
        if not contract_id:
            return f'{prefix}0001'
        try:
            suffix = f'{(int(contract_id.name[-4:]) + 1):04d}'
            return f'{prefix}{suffix}'
        except Exception:
            return f'{prefix}0001'

    name = fields.Char('Number Contract', track_visibility=True)
    code = fields.Char('Code', track_visibility=True, default=_get_default_code)
    vendor_id = fields.Many2one('res.partner',
                                string='Vendor',
                                track_visibility=True)
    effective_date = fields.Date('Effective date', track_visibility=True)
    expiry_date = fields.Date('Expiry date', track_visibility=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 track_visibility=True,
                                 default=lambda self: self.env.company)
    description = fields.Text('Description', track_visibility=True)
    state = fields.Selection([('draft', 'Draft'), ('effective', 'Effective'),
                              ('expiry', 'Expiry'), ('cancel', 'Cancel')],
                             string='State',
                             default='draft',
                             track_visibility=True)

    _sql_constraints = [
        ('check_expiry_date', 'check(expiry_date >= effective_date)',
         'The expiration date must be greater than the effective date.'),
    ]


    def unlink(self):
        contract = self.filtered(lambda item: item.state != 'draft')
        if contract:
            raise ValidationError(
                _("You cannot delete record if the state is not 'Draft'."))
        return super(VendorContract, self).unlink()

    def action_effective(self):
        self.state = 'effective'

    def action_expiry(self):
        self.state = 'expiry'

    def action_cancel(self):
        self.state = 'cancel'

    def action_to_draft(self):
        self.state = 'draft'

    def action_cron_expiry(self):
        today = fields.Date.today()
        contract_ids = self.env['vendor.contract'].search([
            ('expiry_date', '<', today), ('state', '=', 'effective')
        ])
        for contract_id in contract_ids:
            contract_id.action_expiry()