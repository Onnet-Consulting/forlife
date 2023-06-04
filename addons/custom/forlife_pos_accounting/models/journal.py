from odoo import fields, models, api

DEFAULT_ACCOUNT_DOMAIN = "[('deprecated', '=', False), ('company_id', '=', company_id), '|', '&', ('account_type', '=', default_account_type), ('account_type', 'not in', ('asset_receivable', 'liability_payable')), ('id', 'in', account_consignment_tmpl_ids)]"


class InheritAccountJournal(models.Model):
    _inherit = 'account.journal'

    company_consignment_id = fields.Many2one(
        comodel_name='res.partner', string='Consignment Company', index=True,
        domain=[('is_company', '=', True)]
    )

    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain=DEFAULT_ACCOUNT_DOMAIN
    )

    account_consignment_tmpl_ids = fields.Many2many(comodel_name='account.account', compute='_compute_account_consignment_tmpl_ids')

    @api.depends('type')
    def _compute_account_consignment_tmpl_ids(self):
        for rec in self:
            if rec.type == 'general':
                rec.account_consignment_tmpl_ids = self.env['account.account'].search([])
            else:
                rec.account_consignment_tmpl_ids = None
