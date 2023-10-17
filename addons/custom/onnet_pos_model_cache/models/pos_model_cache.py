# -*- coding: utf-8 -*-
import base64
import json
from ast import literal_eval

from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class PosModelCache(models.Model):
    _name = 'pos.model.cache'
    _description = 'Point of Sale Cache'

    cache = fields.Binary(attachment=True)
    domain = fields.Text(required=True)
    model = fields.Char(required=True, index=True)
    model_fields = fields.Text(required=True)

    compute_user_id = fields.Many2one('res.users', 'Cache compute user', required=True)
    compute_company_id = fields.Many2one('res.company', 'Cache compute company', required=True)
    search_context = fields.Text(string="Search Context")
    last_update = fields.Datetime(string="Last update", default=datetime.now())

    CRITICAL_FIELDS = [
        'domain',
        'model',
        'model_fields',
    ]

    @api.model
    def refresh_promotion_model_caches(self):
        caches = self.search([('model', '=', 'promotion.pricelist.item')])
        for cache in caches:
            domain = [('write_date', '>', cache.last_update)]
            cache.refresh_model_cache(domain)

    @api.model
    def refresh_all_model_caches(self):
        self.env['pos.model.cache'].search([]).refresh_cache()

    @api.model
    def refresh_product_model_caches(self):
        caches = self.search([('model', '=', 'product.product')])
        for cache in caches:
            domain = ['|', ('write_date', '>', cache.last_update), ('product_tmpl_id.write_date', '>', cache.last_update)]
            cache.refresh_model_cache(domain)

    def refresh_model_cache(self, validate_domain):
        """
        Recompute the cache data without search_read all records
        model: model name, e.g: product.product, promotion.pricelist.item,...
        """
        self.env = self.with_user(self.compute_user_id.id).env(context={'allowed_company_ids': self.compute_company_id.ids})

        changed_records = self.env[self.model].search(validate_domain)
        changed_records = changed_records.filtered_domain(self.get_model_domain())
        changed_records = changed_records.read(self.get_model_fields())
        record_by_id = {x.get('id'): x for x in changed_records}

        unlink_logging_ids = self.env['ir.logging'].search([
            ('func', '=', 'unlink'),
            ('name', '=', self.model),
            ('create_date', '>=', self.last_update)
        ])
        # get record unlink from logging
        record_unlink_ids = []
        if unlink_logging_ids:
            for log in unlink_logging_ids:
                record_unlink_ids += json.loads(log.message)
        record_unlink_ids = set(record_unlink_ids)

        if changed_records or record_unlink_ids:
            # Lock table for update
            if changed_records:
                model_table_name = self.model.replace(".", "_")
                self.lock_table_for_cache_refresh(model_table_name, changed_records)

            cached_records = self.cache2json()
            idx_to_remove = []
            # Update records
            for idx, cached_record in enumerate(cached_records):
                if cached_record.get('id') in record_by_id:
                    cached_records[idx] = record_by_id[cached_record.get('id')]
                    del record_by_id[cached_record.get('id')]
                # To Remove Record
                if cached_record.get('id') in record_unlink_ids:
                    idx_to_remove.append(idx)

            # Remove unlinked record
            for idx in idx_to_remove:
                del cached_records[idx]

            # Add new record
            cached_records.extend([record_by_id[x] for x in record_by_id])
            self.write({
                'cache': base64.encodebytes(json.dumps(cached_records, default=date_utils.json_default).encode('utf-8')),
                'last_update': datetime.now()
            })

    def lock_table_for_cache_refresh(self, table_name, records):
        """
        Lock the records while updating to avoid missing cache data
        """
        record_ids = [x.get('id') for x in records]
        self.env.cr.execute(
            f"SELECT 1 FROM {table_name} WHERE id IN %(record_ids)s FOR UPDATE NOWAIT",
            {'record_ids': tuple(record_ids)}
        )

        # FIXME: cleaner way to apply extra lock ?
        if table_name == 'product_product':
            product_tmpl_ids = [{'id': x.get('product_tmpl_id')[0]} for x in records]
            self.lock_table_for_cache_refresh('product_template', product_tmpl_ids)


    def refresh_cache(self):
        for cache in self:
            model_obj = self.env[cache.model].with_user(cache.compute_user_id.id).with_company(cache.compute_company_id)
            records = model_obj.search(cache.get_model_domain(), order=self.env[cache.model]._order)
            res = records.read(cache.get_model_fields())
            cache.write({
                'cache': base64.encodebytes(json.dumps(res, default=date_utils.json_default).encode('utf-8')),
                'last_update': datetime.now()
            })

    def get_model_domain(self):
        return literal_eval(self.domain)

    def get_model_fields(self):
        return literal_eval(self.model_fields)

    def cache2json(self):
        return json.loads(base64.decodebytes(self.cache).decode('utf-8'))
