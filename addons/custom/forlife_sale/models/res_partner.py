# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def name_get(self):
        if self._context.get('res_partner_search_mode'):
            return [(record.id, f"{record.name} - {record.ref}") for record in self]
        return super().name_get()
