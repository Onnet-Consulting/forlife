# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models
from odoo.exceptions import Warning, ValidationError
import json
import base64
import pickle
import logging
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")
from datetime import datetime



class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            store_id = self._context.get('store_id')
            mongo_server_rec = self.env['mongo.server.config'].search([('active_record', '=', True), ('store_id', '=', store_id)], limit=1)
            is_indexed_updated = self._context.get('is_indexed_updated')

            if mongo_server_rec:
                if is_indexed_updated and is_indexed_updated[0] and not is_indexed_updated[0].get('time') and mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_updated:
                    return []
                if mongo_server_rec.cache_last_update_time and mongo_server_rec.is_pos_data_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    load_pos_data_type = mongo_server_rec.load_pos_data_from
                    if load_pos_data_type == 'mongo':
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and mongo_server_rec.cache_last_update_time and is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            context = self._context.copy()
                            del context['sync_from_mongo']
                            client = mongo_server_rec.get_client()
                            info = client.server_info()
                            data = self.env['mongo.server.config'].get_products_from_mongo(fields=fields,client=client)
                            if data:
                                return data
                    else:
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            # ****************decode data************************
                            binary_data = mongo_server_rec.pos_product_cache
                            json_data = json.loads(base64.decodebytes(binary_data).decode('utf-8'))
                            data = json_data.values()
                            return list(data)
                else:
                    mongo_server_rec.is_ordinary_loading = True
                    return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        except Exception as e:
            if self._context.get('sync_from_mongo'):
                context = self._context.copy()
                del context['sync_from_mongo']
                self.with_context(context)
            return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)