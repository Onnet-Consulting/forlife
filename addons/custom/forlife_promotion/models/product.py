# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression
import json


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        print(self._context)
        product_exist_list = json.loads(self._context.get('product_exist_list', '{}'))
        if product_exist_list:
            args = expression.AND([[('id', 'not in', product_exist_list)], args])

        return super(ProductProduct, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)
