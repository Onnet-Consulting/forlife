# -*- coding: utf-8 -*-


from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'bravo.model']
    _bravo_table = 'B30BizDoc'
    _bravo_field_sync = ['name', 'date_order', 'company_id', 'partner_id']

    br1 = BravoCharField(odoo_name='name', bravo_name='DocNo')
    br2 = BravoDatetimeField(odoo_name='date_order', bravo_name='DocDate')
    br3 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
    br4 = BravoMany2oneField('res.partner', odoo_name='partner_id', bravo_name='CustomerCode', field_detail='ref')
    br5 = BravoCharField(bravo_name='DocCode', bravo_default='SO')

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_get_update_values(self, values):
        return False

    def bravo_get_delete_sql(self):
        return False

    def action_create_picking(self):
        res = super().action_create_picking()
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return res
        queries = self.bravo_get_insert_sql()
        if queries:
            self.env['sale.order'].sudo().with_delay(channel="root.Bravo").bravo_execute_query(queries)
        return res

    @api.model
    def bravo_get_filter_domain(self):
        return [('state', 'in', ('sale', 'done'))]

    def bravo_filter_records(self):
        records = super().bravo_filter_records()
        return records.filtered(lambda rec: rec.partner_id.group_id !=
                                            self.env.ref('forlife_pos_app_member.partner_group_c'))
