from odoo import fields, models


class InheritAccountJournal(models.Model):
    _inherit = 'account.journal'

    company_consignment_id = fields.Many2one(
        comodel_name='res.partner', string='Consignment Company', index=True,
        domain=[('is_company', '=', True)]
    )

    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict', string='Default Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('account_type', '=', default_account_type)]"
    )
