# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
import json
import base64
import math
from datetime import datetime, timedelta
from odoo.tools import date_utils
import time

import logging
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")


class ModelDataRecord(models.Model):
    _name = 'model.data.record'
    _description = "Model Data Record"

    model_id = fields.Many2one(
        string='Model Name',
        comodel_name='ir.model',
        domain=[('model_id', 'in', ['product.product', 'res.partner'])],
    )
    model_fields = fields.Many2many(
        "ir.model.fields", 'mapping_fields_with_mongo', string="Select Field To Load")
    mongo_config = fields.Many2one(
        string='Mongo Config',
        comodel_name='mongo.server.config',
        ondelete='restrict',
    )

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field = self.field


class PosFastLoadingMessage(models.TransientModel):
    _name = "pos.fast.loading.message"
    _description = "Pos Fast Loading Message"

    text = fields.Text('Message')


class MongoServerConfig(models.Model):
    _name = 'mongo.server.config'
    _description = "Mongo Server Config"
    _rec_name = 'load_pos_data_from'

    mongo_host = fields.Char(string="Host")
    active_record = fields.Boolean(default=False, readonly=True)
    mongo_port = fields.Char(string="Port")
    product_field_ids = fields.Many2many('ir.model.fields', 'product_mapping_with_mongo', string="Additional Product Fields",
                                         domain="[('model_id.model','=','product.product'),('name','not in',['display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id','barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description','product_tmpl_id','tracking'])]")
    partner_field_ids = fields.Many2many('ir.model.fields', 'customer_mapping_with_mongo', string="Additional Partner Fields",
                                         domain="[('model_id.model','=','res.partner'),('name','not in',['name','street','city','state_id','country_id','vat','phone','zip','mobile','email','barcode','write_date','property_account_position_id','property_product_pricelist'])]")
    collection_data = fields.One2many(
        string='Loaded Record',
        comodel_name='model.data.record',
        inverse_name='mongo_config',
    )

    product_last_update_time = fields.Datetime('Product Last Sync Time')
    cache_last_update_time = fields.Datetime('Cache Last Sync Time')
    price_last_update_time = fields.Datetime('Price Last Sync Time')
    partner_last_update_time = fields.Datetime('Customer Last Sync Time')
    is_updated = fields.Boolean("Is updated", default=False)
    partner_all_fields = fields.Boolean('All Partner Fields', default=False)
    product_all_fields = fields.Boolean('All Products Fields', default=False)

    is_product_synced = fields.Boolean('Is Product Synced', default=False)
    is_partner_synced = fields.Boolean('Is Partner Synced', default=False)
    is_pricelist_synced = fields.Boolean('Is Pricelist Synced', default=False)

    pos_product_cache = fields.Binary(string="Pos Product Cache")
    pos_pricelist_cache = fields.Binary(string="Pos Pricelist Cache")
    pos_partner_cache = fields.Binary(string="Pos Partner Cache")

    is_ordinary_loading = fields.Boolean(
        string="Is Loaded Ordinary", default=False)
    is_pos_data_synced = fields.Boolean(
        string="Is All Data Synced", default=False)

    load_pos_data_from = fields.Selection(string="Load Pos Data From", selection=[
                                          ('postgres', 'Postgres'), ('mongo', 'Mongo')], default="postgres")
    pos_live_sync = fields.Selection(string="Pos Syncing", selection=[('realtime', 'Real Time Update'), (
        'notify', 'Only notify when Changes Occur'), ('reload', 'Apply changes on reloading')], default="notify")

    def write(self, vals):
        for obj in self:
            if obj.load_pos_data_from != vals.get('load_pos_data_from') and vals.get('load_pos_data_from'):
                vals.update({
                    'product_last_update_time': False,
                    'cache_last_update_time': False,
                    'price_last_update_time': False,
                    'partner_last_update_time': False,
                    'is_ordinary_loading': True,
                    'is_product_synced': False,
                    'is_pricelist_synced': False,
                    'is_partner_synced': False
                })
        res = super(MongoServerConfig, self).write(vals)
        return res

    @api.constrains('active_record')
    def validate_mongo_server_active_records(self):
        records = self.search([])
        count = 0
        for record in records:
            if record.active_record == True:
                count += 1
        if(count > 1):
            raise ValidationError("You can't have two active mongo configs.")

    def toggle_active_record(self):
        if self.active_record:
            self.active_record = False
        else:
            self.active_record = True

    def check_connection(self):
        client = self.get_client()
        try:
            info = client.server_info()  # Forces a call.
            raise ValidationError("login successfully")
        except ServerSelectionTimeoutError:
            raise ValidationError("server is down.")

    def get_client(self):
        host = self.mongo_host
        port = self.mongo_port
        url = "mongodb://%s:%s" % (host, port)
        try:
            return MongoClient(url)
        except Exception as e:
            raise ValidationError("Exception Occurred : {}".format(e))

    @api.model
    def get_products_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([], limit=1)
        client = mongo_server_rec.get_client()
        fields = kwargs.get('fields')
        if mongo_server_rec.product_field_ids:
            fields = fields + [str(data.name)
                               for data in self.product_field_ids]
        product_operations = self.env['common.cache.notification'].search(
            [('state', '=', 'draft')], order="id asc")
        try:
            info = client.server_info()
            if client:
                database = self._cr.dbname
                if database in client.list_database_names():
                    db = client[database]
                    products_col = db.products
                    product_cur = products_col.find()
                    res = []
                    for record in product_cur:
                        if record.get('id'):
                            if(record.get('_id')):
                                del record['_id']
                            res.append(record)
                    return res
        except Exception as e:
            _logger.info("____________Exception__________:%r", e)
            return False
        return False

    @api.model
    def get_data_on_sync(self, kwargs):
        pos_mongo_config = kwargs.get('mongo_cache_last_update_time')
        config_id = False
        if kwargs.get('config_id'):
            config_id = self.env['pos.config'].browse(kwargs.get('config_id'))
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            data_dict = {
                'products': [],
                'pricelist_items': [],
                'partners': [],
                'mongo_config': mongo_server_rec.cache_last_update_time,
                'price_deleted_record_ids': [],
                # 'price_deleted_records':[],
                'partner_deleted_record_ids': [],
                'product_deleted_record_ids': [],
                'sync_method': mongo_server_rec.pos_live_sync
            }
            try:
                ctx = self._context.copy()
                ctx.update({
                    'company_id': kwargs.get('company_id'),
                })
                self.env['common.cache.notification'].with_context(ctx).get_common_changes()
                product_data = []
                pricelist_item_data = []
                new_cache_records = self.env['common.cache.notification'].search(
                    [('create_date', '>=', pos_mongo_config)])

                if new_cache_records:
                    product_record_ids = []
                    price_record_ids = []
                    partner_record_ids = []
                    partner_deleted_record_ids = []
                    price_deleted_record_ids = []
                    product_deleted_record_ids = []
                    price_res = []
                    product_res = []
                    partner_res = []
                    for record in new_cache_records:
                        if record.model_name == 'product.product':
                            if record.operation == 'DELETE':
                                product_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                product_record_ids.append(record.record_id)
                        # elif record.model_name == 'res.partner':
                        #     if record.operation == 'DELETE':
                        #         partner_deleted_record_ids.append(
                        #             record.record_id)
                        #     else:
                        #         partner_record_ids.append(record.record_id)
                        elif record.model_name == 'product.pricelist.item':
                            if record.operation == 'DELETE':
                                price_deleted_record_ids.append(
                                    record.record_id)
                            elif record.operation == 'UPDATE':
                                price_record_ids.append(record.record_id)
                                price_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                price_record_ids.append(record.record_id)

                    load_pos_data_type = mongo_server_rec.load_pos_data_from
                    if load_pos_data_type == 'mongo':
                        client = mongo_server_rec.get_client()
                        if client:
                            database = self._cr.dbname
                            if database in client.list_database_names():
                                db = client[database]
                                if len(price_record_ids):
                                    pricelist_items_col = db.pricelist_items
                                    pricelist_item_data = pricelist_items_col.find(
                                        {'id': {'$in': price_record_ids}})
                                    for record in pricelist_item_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            price_res.append(record)
                                    pricelist_item_deleted_data = pricelist_items_col.find(
                                        {'id': {'$in': price_deleted_record_ids}})
                                if len(product_record_ids):
                                    products_col = db.products
                                    product_data = products_col.find(
                                        {'id': {'$in': product_record_ids}})
                                    for record in product_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            product_res.append(record)
                                if len(partner_record_ids):
                                    partners_col = db.partners
                                    partner_data = partners_col.find(
                                        {'id': {'$in': partner_record_ids}})
                                    for record in partner_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            partner_res.append(record)
                    else:
                        if len(price_record_ids):
                            binary_data = mongo_server_rec.pos_pricelist_cache
                            json_data = json.loads(
                                base64.decodebytes(binary_data).decode('utf-8'))
                            for obj in json_data:
                                if int(obj) in price_record_ids:
                                    price_res.append(json_data.get(obj))

                        if len(product_record_ids):
                            binary_data = mongo_server_rec.pos_product_cache
                            json_data = json.loads(
                                base64.decodebytes(binary_data).decode('utf-8'))
                            for obj in json_data:
                                if int(obj) in product_record_ids:
                                    product_res.append(json_data.get(obj))

                        # if len(partner_record_ids):
                        #     binary_data = mongo_server_rec.pos_partner_cache
                        #     json_data = json.loads(
                        #         base64.decodebytes(binary_data).decode('utf-8'))
                        #     for obj in json_data:
                        #         if int(obj) in partner_record_ids:
                        #             partner_res.append(json_data.get(obj))

                    data_dict.update({
                        'products': product_res,
                        'pricelist_items': price_res,
                        # 'partners': partner_res,
                        'mongo_config': mongo_server_rec.cache_last_update_time,
                        'price_deleted_record_ids': price_deleted_record_ids,
                        # 'partner_deleted_record_ids': partner_deleted_record_ids,
                        'product_deleted_record_ids': product_deleted_record_ids
                    })
                return data_dict
            except Exception as e:
                return data_dict
                _logger.info("**********Exception*****************:%r", e)

    def sync_partners(self):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            fields = ['name', 'street', 'city', 'country_id', 'vat', 'color', 'phone', 'zip', 'mobile', 'email', 'barcode', 'write_date',
                      'property_account_position_id', 'property_product_pricelist', 'company_name', 'property_supplier_payment_term_id', 'active']
            if self.partner_field_ids:
                fields = fields + [str(data.name)
                                   for data in self.partner_field_ids]
            if self.partner_all_fields:
                if mongo_server_rec.load_pos_data_from == 'postgres':
                    customer_fields = self.env['ir.model'].sudo().search(
                        [('model', '=', 'res.partner')]).field_id
                    new_fields = [
                        i.name for i in customer_fields if i.ttype != 'binary']
                    temp_fields = set(fields).union(set(new_fields))
                    fields = list(temp_fields)
                else:
                    fields = []
                # fields = []
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            partners_synced = 0
            p_data = self.env['res.partner'].search([])
            if load_pos_data_type == 'mongo':
                client = self.get_client()
                databases = client.list_database_names()
                database = self._cr.dbname
                if database in databases:
                    db = client[database]
                    db.partners.drop()
                    partners_col = db.partners

                    for count in range(math.ceil(len(p_data) / 1000)):
                        partners_data = []
                        data_to_add = p_data[count * 1000:(count + 1) * 1000]
                        for record in range(math.ceil(len(data_to_add) / 100)):
                            data_to_find = data_to_add[record *
                                                       100:(record + 1) * 100]
                            pro_data = data_to_find.read(fields)
                            if len(pro_data):
                                partners_data.extend(pro_data)
                        partners_col.insert_many(partners_data)
                    partners_synced = len(p_data)
                else:
                    db = client[database]
                    partners_col = db.partners
                    for count in range(math.ceil(len(p_data) / 1000)):
                        partners_data = []
                        data_to_add = p_data[count * 1000:(count + 1) * 1000]
                        for record in range(math.ceil(len(data_to_add) / 100)):
                            data_to_find = data_to_add[record *
                                                       100:(record + 1) * 100]
                            pro_data = data_to_find.read(fields)
                            if len(pro_data):
                                partners_data.extend(pro_data)
                        partners_col.insert_many(partners_data)
                    partners_synced = len(p_data)
            else:
                partner_data = {}
                for count in range(math.ceil(len(p_data) / 1000)):
                    partner_dict = {}
                    data_to_add = p_data[count * 1000:(count + 1) * 1000]
                    for record in range(math.ceil(len(data_to_add) / 100)):
                        data_to_find = data_to_add[record * 100:(record + 1) * 100]
                        pro_data = data_to_find.read(fields)
                        for partner_conv_data in pro_data:
                            partner_dict[partner_conv_data.get(
                                'id')] = partner_conv_data
                    partner_data.update(partner_dict)
                partners_synced = len(p_data)

                data = {'pos_partner_cache': base64.encodebytes(
                    json.dumps(partner_data, default=date_utils.json_default).encode('utf-8'))}
                mongo_server_rec.write(data)

            records_to_delete = self.env['common.cache.notification'].search(
                [('model_name', '=', 'res.partner')])
            if len(records_to_delete):
                records_to_delete.unlink()
            mongo_server_rec.partner_last_update_time = datetime.now()
            mongo_server_rec.is_partner_synced = True
            try:
                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    mongo_server_rec.is_pos_data_synced = True
                    self.env['common.cache.notification'].get_common_changes()
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Customers have been synced.".format(partners_synced)})
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    def sync_products(self):
        start_time = time.time()
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            fields = ['active', 'display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                      'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'company_id',
                      'product_tmpl_id', 'tracking', 'available_in_pos']
            products_synced = 0
            if mongo_server_rec.product_field_ids:
                fields = list(set(fields + [str(data.name)
                                            for data in self.product_field_ids]))
            if self.product_all_fields:
                if mongo_server_rec.load_pos_data_from == 'postgres':
                    product_fields = self.env['ir.model'].sudo().search(
                        [('model', '=', 'product.product')]).field_id
                    new_fields = [
                        i.name for i in product_fields if i.ttype != 'binary']
                    temp_fields = set(fields).union(set(new_fields))
                    fields = list(temp_fields)
                else:
                    fields = []
            p_data = self.env['product.product'].search(
                [['sale_ok', '=', True], ['available_in_pos', '=', True]])
            _logger.info("--- %s seconds in search---" %
                         (time.time() - start_time))
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            if load_pos_data_type == 'mongo':
                try:
                    client = self.get_client()
                    databases = client.list_database_names()
                    database = self._cr.dbname
                    if database in databases:
                        db = client[database]
                        db.products.drop()
                        products_col = db.products
                        for count in range(math.ceil(len(p_data) / 1000)):
                            product_data = []
                            data_to_add = p_data[count * 1000:(count + 1) * 1000]
                            for record in range(math.ceil(len(data_to_add) / 100)):
                                data_to_find = data_to_add[record *
                                                           100:(record + 1) * 100]
                                pro_data = data_to_find.read(fields)
                                if len(pro_data):
                                    product_data.extend(pro_data)
                            products_col.insert_many(product_data)
                        products_synced = len(p_data)

                    else:
                        db = client[database]
                        products_col = db.products

                        for count in range(math.ceil(len(p_data) / 1000)):
                            product_data = []
                            data_to_add = p_data[count * 1000:(count + 1) * 1000]
                            for record in range(math.ceil(len(data_to_add) / 100)):
                                data_to_find = data_to_add[record *
                                                           100:(record + 1) * 100]
                                pro_data = data_to_find.read(fields)
                                if len(pro_data):
                                    product_data.extend(pro_data)
                            products_col.insert_many(product_data)
                        products_synced = len(p_data)
                except ServerSelectionTimeoutError:
                    raise ValidationError("server is down.")
            else:
                products_data = {}
                for count in range(math.ceil(len(p_data) / 1000)):
                    product_dict = {}
                    data_to_add = p_data[count * 1000:(count + 1) * 1000]
                    for record in range(math.ceil(len(data_to_add) / 100)):
                        data_to_find = data_to_add[record * 100:(record + 1) * 100]
                        pro_data = data_to_find.read(fields)
                        _logger.info("--- %s seconds in each read ---" %
                                     (time.time() - start_time))
                        for product_conv_data in pro_data:
                            product_dict[product_conv_data.get(
                                'id')] = product_conv_data
                        # product_dict = {product_conv_data['id']:product_conv_data for product_conv_data in pro_data}
                    products_data.update(product_dict)
                    _logger.info("--- %s seconds in each update ---" %
                                 ((time.time() - start_time),))
                products_synced = len(p_data)
                _logger.info("--- %s seconds in read ---" %
                             (time.time() - start_time))
                data = {
                    'pos_product_cache': base64.encodebytes(json.dumps(products_data, default=date_utils.json_default).encode('utf-8')),
                    'product_last_update_time': datetime.now(),
                    'cache_last_update_time': datetime.now(),
                    'is_product_synced': True
                }
                mongo_server_rec.write(data)
                self._cr.commit()
                _logger.info("--- %s seconds in write---" %
                             (time.time() - start_time))
            records_deleted = self.env['common.cache.notification'].search(
                [('model_name', '=', 'product.product')])
            if len(records_deleted):
                records_deleted.unlink()
            try:
                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    mongo_server_rec.is_pos_data_synced = True
                    self.env['common.cache.notification'].get_common_changes()
                # mongo_server_rec.product_last_update_time = datetime.now()
                # mongo_server_rec.is_product_synced = True
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Products have been synced.".format(products_synced)})
                _logger.info("--- %s seconds ---" % (time.time() - start_time))
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    def sync_pricelist_items(self):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        # try:
        if mongo_server_rec:
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            pricelist_items_synced = 0
            records = self.env['product.pricelist.item'].search([])
            fields = ['__last_update', 'active', 'base', 'categ_id', 'base_pricelist_id', 'company_id', 'compute_price', 'create_date', 'create_uid', 'currency_id', 'date_end', 'date_start', 'display_name', 'fixed_price', 'id',
                      'min_quantity', 'name', 'percent_price', 'price', 'price_discount', 'price_max_margin', 'price_min_margin', 'price_round', 'price_surcharge', 'pricelist_id', 'product_id', 'product_tmpl_id', 'write_date', 'write_uid']
            if load_pos_data_type == 'mongo':
                client = self.get_client()
                databases = client.list_database_names()
                database = self._cr.dbname
                if database in databases:
                    db = client[database]
                    db.pricelist_items.drop()
                    pricelist_items_col = db.pricelist_items
                    new_data = []
                    count = 0
                    for data in records:
                        field_data = data.read(fields)
                        count += 1
                        date_start, date_end = (False, False)
                        if data.date_start:
                            date_start = datetime(
                                data.date_start.year, data.date_start.month, data.date_start.day) or False
                        if data.date_end:
                            date_end = datetime(
                                data.date_end.year, data.date_end.month, data.date_end.day) or False
                        if date_start:
                            field_data[0]['date_start'] = date_start
                        if date_end:
                            field_data[0]['date_end'] = date_end
                        new_data.extend(field_data)
                    if len(new_data):
                        for count in range(math.ceil(len(new_data) / 1000)):
                            data_to_add = new_data[count * 1000:(count + 1) * 1000]
                            pricelist_items_col.insert_many(data_to_add)
                        pricelist_items_synced = len(new_data)

                else:
                    db = client[database]
                    pricelist_items_col = db.pricelist_items
                    new_data = []
                    count = 0
                    for data in records:
                        field_data = data.read(fields)
                        count += 1
                        date_start, date_end = (False, False)
                        if data.date_start:
                            date_start = datetime(
                                data.date_start.year, data.date_start.month, data.date_start.day) or False
                        if data.date_end:
                            date_end = datetime(
                                data.date_end.year, data.date_end.month, data.date_end.day) or False
                        if date_start:
                            field_data[0]['date_start'] = date_start
                        if date_end:
                            field_data[0]['date_end'] = date_end
                        new_data.extend(field_data)
                    if len(new_data):
                        for count in range(math.ceil(len(new_data) / 1000)):
                            data_to_add = new_data[count * 1000:(count + 1) * 1000]
                            pricelist_items_col.insert_many(data_to_add)
                        pricelist_items_synced = len(new_data)
            else:
                pricelist_data = {}
                for count in range(math.ceil(len(records) / 1000)):
                    pricelist_dict = {}
                    data_to_add = records[count * 1000:(count + 1) * 1000]
                    for record in range(math.ceil(len(data_to_add) / 100)):
                        data_to_find = data_to_add[record * 100:(record + 1) * 100]
                        price_data = data_to_find.read([])
                        for pricelist_conv_data in price_data:
                            pricelist_dict[pricelist_conv_data.get(
                                'id')] = pricelist_conv_data
                    pricelist_data.update(pricelist_dict)
                pricelist_items_synced = len(records)
                data = {'pos_pricelist_cache': base64.encodebytes(
                    json.dumps(pricelist_data, default=date_utils.json_default).encode('utf-8'))}
                mongo_server_rec.write(data)
            records_to_delete = self.env['common.cache.notification'].search(
                [('model_name', '=', 'product.pricelist.item')])
            if len(records_to_delete):
                records_to_delete.unlink()
            mongo_server_rec.price_last_update_time = datetime.now()
            mongo_server_rec.is_pricelist_synced = True
            try:
                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    mongo_server_rec.is_pos_data_synced = True
                self.env['common.cache.notification'].get_common_changes()
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Pricelist Items have been synced.".format(pricelist_items_synced)})
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    @api.model
    def get_pricelist_items_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            client = mongo_server_rec.get_client()
            try:
                info = client.server_info()
                if client:
                    database = self._cr.dbname
                    if database in client.list_database_names():
                        db = client[database]
                        pricelist_items_col = db.pricelist_items
                        pricelist_items = pricelist_items_col.find(
                            ({'id': {'$in': kwargs.get('pricelist_item_ids')}}))
                        res = []
                        for record in pricelist_items:
                            if record.get('id'):
                                if(record.get('_id')):
                                    del record['_id']
                                res.append(record)
                        return res
            except ServerSelectionTimeoutError:
                return False
            return False

    @api.model
    def get_customer_data_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            try:
                if kwargs.get('client'):
                    client = kwargs.get('client')
                else:
                    client = mongo_server_rec.get_client()
                    info = client.server_info()
                if client:
                    database = self._cr.dbname
                    if database in client.list_database_names():
                        db = client[database]
                        partner_col = db.partners
                        partner_cur = partner_col.find()

                        res = []
                        for record in partner_col.find():
                            if record.get('id'):
                                if(record.get('_id')):
                                    del record['_id']
                                res.append(record)
                        return res
            except Exception as e:
                _logger.info(
                    "------------------except(*****************):%r", e)
                return False
            return False
