# -*- coding: utf-8 -*-


from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'bravo.model']
    _bravo_table = 'B30BizDoc'
    _bravo_field_sync = ['name', 'date_approve', 'company_id', 'partner_id']

    br1 = BravoCharField(odoo_name='name', bravo_name='DocNo')
    br2 = BravoDatetimeField(odoo_name='date_approve', bravo_name='DocDate')
    br3 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='CompanyCode', field_detail='code')
    br4 = BravoMany2oneField('res.partner', odoo_name='partner_id', bravo_name='CustomerCode', field_detail='ref')
    br5 = BravoCharField(bravo_name='DocCode', bravo_default='PO')

    @api.model
    def bravo_get_default_insert_value(self):
        return {
            'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'",
        }

    def bravo_get_update_values(self, values):
        return False

    def bravo_get_delete_sql(self):
        return False

    def action_approved(self):
        res = super().action_approved()
        queries = self.bravo_get_insert_sql()
        self.env['purchase.order'].sudo().with_delay(channel="root.Bravo").bravo_execute_query(queries)
        return res

    @api.model
    def bravo_get_filter_domain(self):
        return [('custom_state', '=', 'approved')]

    def bravo_filter_records(self):
        records = super().bravo_filter_records()
        return records.filtered(lambda rec: rec.partner_id.group_id !=
                                            self.env.ref('forlife_pos_app_member.partner_group_c'))
