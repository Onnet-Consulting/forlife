# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from datetime import datetime, timedelta
from odoo.exceptions import Warning, ValidationError
from odoo import models, fields, api, _
import _pickle as cPickle
import logging
import json
import base64
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")


class CommonCacheNotification(models.Model):
    _name = 'common.cache.notification'
    _description = "Common Cache Notification"

    model_name = fields.Char('Model Name')
    record_id = fields.Integer('Record Id')
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'), ('done', 'Done'), ('failed', 'Failed')],
        default='draft'
    )
    operation = fields.Selection(
        selection=[('DELETE', 'DELETE'), ('UPDATE', 'UPDATE'), ('CREATE', 'CREATE')])
    change_vals = fields.Text(string="Fields Changed")
    store_id = fields.Many2many('store', string=_('Store'))


    @api.model
    def create(self, vals):
        res = super(CommonCacheNotification, self).create(vals)
        try:
            mongo_server_rec = self.env['mongo.server.config'].search(
                [('active_record', '=', True)], limit=1)
            mongo_server_rec.is_updated = False
        except Exception as e:
            _logger.info("****************Exception***********:%r", e)
        return res

    @api.model
    def get_common_changes(self):
        ctx = self._context.copy()

        records = self.sudo().search([('state', '!=', 'done')])
        mongo_server_rec = self.env['mongo.server.config'].search(
            [('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            product_fields = ['display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                            'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                            'product_tmpl_id', 'tracking', 'active', 'available_in_pos', '__last_update']

            if mongo_server_rec.product_field_ids:
                product_fields = list(set(
                    product_fields + [str(data.name) for data in mongo_server_rec.product_field_ids]))

            if mongo_server_rec.product_all_fields:
                if mongo_server_rec.load_pos_data_from == 'postgres':
                    fields = self.env['ir.model'].sudo().search(
                        [('model', '=', 'product.product')]).field_id
                    new_fields = [i.name for i in fields if i.ttype != 'binary']
                    temp_fields = set(product_fields).union(set(new_fields))
                    product_fields = list(temp_fields)
                else:
                    product_fields = []

            load_pos_data_type = mongo_server_rec.load_pos_data_from
            self.with_context(ctx).sync_pos_cache(mongo_server_rec, records, product_fields)

            updated_records = self.search(
                [('state', '=', 'done')], order="id desc")
            records_to_delete = []
            if len(updated_records):
                records_to_delete = updated_records[500:]
            if len(records_to_delete):
                records_to_delete.unlink()
            if not mongo_server_rec.cache_last_update_time and not mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_product_synced:
                mongo_server_rec.cache_last_update_time = datetime.now()

    def sync_pos_cache(self, mongo_server_rec, records, product_fields):
        if(len(records)) and mongo_server_rec:
            partner_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_partner_cache).decode('utf-8')) if mongo_server_rec.pos_partner_cache else False
            product_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_product_cache).decode('utf-8')) if mongo_server_rec.pos_product_cache else False
            pricelist_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_pricelist_cache).decode('utf-8')) if mongo_server_rec.pos_pricelist_cache else False
            for record in records:
                # try:
                if record.operation == "UPDATE" or record.operation == "CREATE":
                    values = []
                    if record.model_name == 'product.product':
                        product = self.env[record.model_name].browse(
                            record.record_id)
                        product_data = {}
                        if product:
                            pro_data = product.sudo().with_company(self.env['res.company'].browse(self._context.get('company_id'))).read(product_fields)
                            if len(pro_data):
                                product_conv_data = pro_data[0]
                                image_fields = ['image_1024', 'image_128', 'image_1920', 'image_256', 'image_512', 'image_variant_1024',
                                                'image_variant_128', 'image_variant_1920', 'image_variant_256', 'image_variant_512']
                                initial_keys = pro_data[0].keys()
                                new_field_list = set(image_fields).intersection(
                                    set(initial_keys))
                                for field in new_field_list:
                                    del product_conv_data[field]
                                if len(product_conv_data):
                                    product_data = product_conv_data
                        if len(product_data) and product_json_data:
                            product_json_data[product_data.get("id")] = product_data
                        record.state = 'done'

                elif record.operation == "DELETE":
                    if record.model_name == 'res.partner' and partner_json_data:
                        if partner_json_data.get(str(record.record_id)):
                            del partner_json_data[str(record.record_id)]
                    elif record.model_name == 'product.product' and product_json_data:
                        if product_json_data.get(str(record.record_id)):
                            del product_json_data[str(record.record_id)]
                    elif record.model_name == 'product.pricelist.item' and pricelist_json_data:
                        if pricelist_json_data.get(str(record.record_id)):
                            del pricelist_json_data[str(record.record_id)]
                    record.state = 'done'
            if not mongo_server_rec.is_ordinary_loading:
                mongo_server_rec.cache_last_update_time = datetime.now()
            mongo_server_rec.is_updated = True
            if partner_json_data:
                updated_data = base64.encodebytes(
                    json.dumps(partner_json_data, default=date_utils.json_default).encode('utf-8'))
                if updated_data:
                    data_to_add = {
                        'pos_partner_cache': updated_data}
                    mongo_server_rec.write(data_to_add)
                mongo_server_rec.partner_last_update_time = datetime.now()
            if product_json_data:
                updated_data = base64.encodebytes(
                    json.dumps(product_json_data, default=date_utils.json_default).encode('utf-8'))
                if updated_data:
                    data_to_add = {
                        'pos_product_cache': updated_data}
                    mongo_server_rec.write(data_to_add)
                mongo_server_rec.product_last_update_time = datetime.now()
            if pricelist_json_data:
                updated_data = base64.encodebytes(
                    json.dumps(pricelist_json_data, default=date_utils.json_default).encode('utf-8'))
                if updated_data:
                    data_to_add = {
                        'pos_pricelist_cache': updated_data}
                    mongo_server_rec.write(data_to_add)
                mongo_server_rec.price_last_update_time = datetime.now()
        else:
            mongo_server_rec.is_updated = True