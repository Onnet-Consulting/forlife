# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.osv import expression


class Partner(models.Model):
    _inherit = "res.partner"

    @api.depends('is_company', 'name', 'parent_id.display_name', 'type', 'company_name', 'barcode')
    def _compute_display_name(self):
        names = dict(self.with_context({}).name_get())
        for partner in self:
            partner.display_name = names.get(partner.id)

    def _get_name(self):
        if self.barcode and self.name:
            return self.barcode + ' ' + self.name
        else:
            return super(Partner, self)._get_name()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name and self._context.get('salary_accounting_config', False):
            domain = ['|', ('barcode', 'ilike', name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
