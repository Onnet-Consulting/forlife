# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        pos_brand = self.config_id.store_id.brand_id
        pos_store_contact = self.config_id.store_id.contact_id
        pos_store_info = {
            "address": pos_store_contact.contact_address_complete,
            "phone": pos_store_contact.phone
        }
        # get receipt footer from res.brand field config
        loaded_data['pos_brand_info'].update({
            "pos_receipt_footer": pos_brand.pos_receipt_footer,
            "mobile_app_url": pos_brand.mobile_app_url
        })
        loaded_data.update({
            "pos_store_info": pos_store_info
        })
        return loaded_data
