# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    partner_id = fields.Many2one(default=False, readonly=True)

    def prepare_partner_value(self):
        self.ensure_one()
        # FIXME: add phone number here (where to get phone number)
        return {
            "company_type": "person",
            "group_id": self.env.ref('forlife_pos_app_member.partner_group_5').id,
            "name": self.name,
            "ref": self.code
        }

    def create_partner(self):
        # TODO: create partner here
        for warehouse in self:
            partner_value = warehouse.prepare_partner_value()
