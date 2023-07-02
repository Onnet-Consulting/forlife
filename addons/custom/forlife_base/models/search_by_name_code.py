# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SearchByNameCode(models.AbstractModel):
    _name = 'search.by.name.code'
    _description = 'search by name code'

    def name_get(self):
        if self._context.get('show_code_name'):
            result = []
            for r in self:
                name = f"[{r.code or ''}] {r.name or ''}"
                result.append((r.id, name))
            return result
        return super().name_get()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('show_code_name') and name:
            args = list(args or []) + ['|', ('code', 'ilike', name), ('name', 'ilike', name)]
            return self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)


