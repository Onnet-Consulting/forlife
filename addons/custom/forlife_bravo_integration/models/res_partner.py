# -*- coding:utf-8 -*-

from odoo import api, fields, models
# from odoo.addons.forlife_bravo_integration.models.bravo_fields import BravoCharField
from ..fields import BravoCharField


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'bravo.model']

    br_field_name = BravoCharField(odoo_name="name", bravo_name="Name")


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Base, self).create(vals_list)
        if issubclass(type(self), type(self.env['bravo.model'])):
            all_fields = self.fields_get(allfields=['br_field_name'], attributes=['odoo_name', 'bravo_name'])
            x = 1
        return res
