# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        pos_brand = self.config_id.store_id.brand_id
        loaded_data['pos_brand_info'].update({
            "pos_receipt_footer": pos_brand.pos_receipt_footer
        })
        return loaded_data
        # pos_brand_info = {
        #     "code": pos_brand.code,
        #     "id": pos_brand.id,
        #     "pos_receipt_footer": pos_brand.pos_receipt_footer}
        # loaded_data.update({
        #     'pos_brand_info': pos_brand_info
        # })
        # return loaded_data
