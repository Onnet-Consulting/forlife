# -*- coding: utf-8 -*-


from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'bravo.model']
    _bravo_table = 'B30BizDoc'

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

    def button_confirm(self):
        res = super().button_confirm()
        # FIXME: push below function to job queue
        self.sudo().bravo_insert()
        return res

    @api.model
    def bravo_get_filter_domain(self):
        return [('state', 'in', ('purchase', 'done'))]
