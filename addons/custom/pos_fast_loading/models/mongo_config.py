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
    _rec_name = 'name'

    name = fields.Char(string="Name", compute="_compute_name", store=True)
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

    store_id = fields.Many2one(string=_("store"), comodel_name="store", required=True)

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

    pos_pricelist_cache = fields.Binary(string="Pos Pricelist Cache")
    pos_partner_cache = fields.Binary(string="Pos Partner Cache")
    pos_product_cache = fields.Binary(string="Pos Product Cache")

    is_ordinary_loading = fields.Boolean(
        string="Is Loaded Ordinary", default=False)
    is_pos_data_synced = fields.Boolean(
        string="Is All Data Synced", default=False)

    load_pos_data_from = fields.Selection(string="Load Pos Data From", selection=[
                                          ('postgres', 'Postgres'), ('mongo', 'Mongo')], default="postgres")
    pos_live_sync = fields.Selection(string="Pos Syncing", selection=[('realtime', 'Real Time Update'), (
        'notify', 'Only notify when Changes Occur'), ('reload', 'Apply changes on reloading')], default="notify")

    _sql_constraints = [
            ('store_unique', 'unique (store_id)', 'The combination store_id already exists!'),
        ]

    @api.depends('store_id')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.store_id and rec.store_id.name or "draft"

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

    def toggle_active_record(self):
        if self.active_record:
            self.active_record = False
        else:
            self.active_record = True

    @api.model
    def get_data_on_sync(self, kwargs):
        pos_mongo_config = kwargs.get('mongo_cache_last_update_time')
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            data_dict = {
                'products': [],
                'pricelist_items': [],
                'partners': [],
                'mongo_config': mongo_server_rec.cache_last_update_time,
                'price_deleted_record_ids': [],
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
                new_cache_records = self.env['common.cache.notification'].search(
                    [('create_date', '>=', pos_mongo_config)])

                if new_cache_records:
                    product_record_ids = []
                    product_deleted_record_ids = []
                    product_res = []
                    for record in new_cache_records:
                        if record.model_name == 'product.product':
                            if record.operation == 'DELETE':
                                product_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                product_record_ids.append(record.record_id)

                    if len(product_record_ids):
                        binary_data = mongo_server_rec.pos_product_cache
                        json_data = json.loads(
                            base64.decodebytes(binary_data).decode('utf-8'))
                        for obj in json_data:
                            if int(obj) in product_record_ids:
                                product_res.append(json_data.get(obj))
                    data_dict.update({
                        'products': product_res,
                        'mongo_config': mongo_server_rec.cache_last_update_time,
                        'product_deleted_record_ids': product_deleted_record_ids
                    })
                return data_dict
            except Exception as e:
                return data_dict
                _logger.info("**********Exception*****************:%r", e)

    def _get_products_by_store(self, store):
        # query = 'SELECT pp.id AS ppid, pt.id AS ptid, SUM(sq.quantity) FROM stock_quant sq JOIN product_product pp ON pp.id = sq.product_id JOIN product_template pt ON pt.id = pp.product_tmpl_id WHERE sq.location_id in (SELECT id FROM stock_location WHERE warehouse_id = 1) and quantity > 0 GROUP BY ppid, ptid'
        query = '''SELECT pp.id FROM product_product pp JOIN product_template pt ON pt.id = pp.product_tmpl_id WHERE pp.id in (SELECT id FROM stock_quant WHERE location_id in (SELECT id FROM stock_location WHERE warehouse_id =  %(warehouse_id)s) and quantity > 0) AND pt.sale_ok = true AND pt.available_in_pos = true;'''
        self.env.cr.execute(query, {'warehouse_id': store.warehouse_id.id})
        data = self.env.cr.fetchall()
        return data

    def sync_products(self):
        start_time = time.time()
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec and self.store_id.warehouse_id:
            fields = ['active', 'display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                      'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'company_id',
                      'product_tmpl_id', 'tracking', 'available_in_pos']
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

            product_ids = self._get_products_by_store(self.store_id)
            p_data = self.env['product.product'].search([['id', 'in', product_ids]])

            _logger.info("--- %s seconds in search---" %
                         (time.time() - start_time))

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
                if mongo_server_rec.is_product_synced:
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
