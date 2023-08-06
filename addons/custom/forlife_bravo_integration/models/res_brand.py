# -*- coding:utf-8 -*-

from ..fields import *


class ResBrand(models.Model):
    _name = 'res.brand'
    _inherit = ['res.brand', 'bravo.model']
    _bravo_table = 'B20Brand'
    _bravo_field_sync = ['code', 'name']

    br1 = BravoCharField(odoo_name='code', bravo_name='Code', identity=True)
    br2 = BravoCharField(odoo_name='name', bravo_name='Name')

    @api.model
    def bravo_push_existing_brands(self):
        if not self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            return True
        exist_brands = self.env.ref("forlife_point_of_sale.brand_format") + \
                       self.env.ref("forlife_point_of_sale.brand_tokyolife")
        exist_brands.sudo().with_delay(channel="root.Bravo").bravo_insert_with_check_existing()
        return True
