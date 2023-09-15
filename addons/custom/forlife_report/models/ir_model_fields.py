# -*- coding:utf-8 -*-

from odoo import api, fields, models


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def name_get(self):
        if self._context.get('report_permission'):
            result = []
            for f in self:
                result.append((f.id, f"{f.field_description} ({f.name} - {f.relation})"))
            return result
        return super().name_get()
