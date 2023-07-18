# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if name and self._context.get('salary_accounting_config', False):
            args = args or []
            domain = ['|', ('ref', 'ilike', name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)
