# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_pos_app_member.models.res_utility import get_valid_phone_number, is_valid_phone_number
from odoo.exceptions import ValidationError, UserError


class CreateWarehousePartner(models.TransientModel):
    _name = 'create.warehouse.partner'
    _description = 'Create Warehouse Partner Wizard'

    phone = fields.Char(required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)

    @api.model
    def default_get(self, fields):
        """ Allow support of active_id / active_model instead of jut default_lead_id
        to ease window action definitions, and be backward compatible. """
        result = super(CreateWarehousePartner, self).default_get(fields)

        if not result.get('warehouse_id') and self.env.context.get('active_id'):
            result['warehouse_id'] = self.env.context.get('active_id')

        if result.get('warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(result['warehouse_id'])
            if warehouse.partner_id:
                raise ValidationError(_("Partner of warehouse %s already exist") % warehouse.name)

        return result

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            if rec.phone and not is_valid_phone_number(rec.phone):
                raise ValidationError(_('Invalid phone number - %s') % rec.phone)

    def create_partner(self):
        warehouse_id = self.env.context.get('active_id')
        if not warehouse_id:
            raise ValidationError(_("You must call this action from warehouse form view!"))
        partner_values = self.prepare_partner_value()
        partner = self.env['res.partner'].create(partner_values)
        self.warehouse_id.write({'partner_id': partner.id})
        return True

    def prepare_partner_value(self):
        self.ensure_one()
        warehouse = self.warehouse_id
        return {
            "company_type": "person",
            "group_id": self.env.ref('forlife_pos_app_member.partner_group_5').id,
            "name": warehouse.name,
            "ref": warehouse.code,
            "phone": self.phone
        }
