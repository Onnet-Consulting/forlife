# -*- coding: utf-8 -*-


from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'bravo.model']
    _bravo_table = 'B30BizDoc'

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

    def action_confirm(self):
        res = super().action_confirm()
        # FIXME: push below function to job queue
        self.sudo().bravo_insert()
        return res

    @api.model
    def bravo_get_filter_domain(self):
        return [('state', 'in', ('sale', 'done'))]
