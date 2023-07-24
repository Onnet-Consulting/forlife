# -*- coding: utf-8 -*-
import base64
import json
from ast import literal_eval

from odoo import models, fields, api
from odoo.tools import date_utils


class PosModelCache(models.Model):
    _name = 'pos.model.cache'
    _description = 'Point of Sale Cache'

    cache = fields.Binary(attachment=True)
    domain = fields.Text(required=True)
    model = fields.Char(required=True, index=True)
    model_fields = fields.Text(required=True)

    config_id = fields.Many2one('pos.config', ondelete='cascade', required=True)
    compute_user_id = fields.Many2one('res.users', 'Cache compute user', required=True)

    @api.model
    def refresh_all_model_caches(self):
        self.env['pos.model.cache'].search([]).refresh_cache()

    def refresh_cache(self):
        for cache in self:
            model_obj = self.env[self.model].with_user(cache.compute_user_id.id)
            records = model_obj.search(cache.get_model_domain(), order=self.env[self.model]._order)
            _ctx = records.with_context(pricelist=cache.config_id.pricelist_id.id,
                                        display_default_code=False, lang=cache.compute_user_id.lang)
            res = _ctx.read(cache.get_model_fields())
            cache.write({
                'cache': base64.encodebytes(json.dumps(res, default=date_utils.json_default).encode('utf-8')),
            })

    @api.model
    def get_model_domain(self):
        return literal_eval(self.domain)

    @api.model
    def get_model_fields(self):
        return literal_eval(self.model_fields)

    def cache2json(self):
        return json.loads(base64.decodebytes(self.cache).decode('utf-8'))


class pos_config(models.Model):
    _inherit = 'pos.config'

    @api.depends('cache_ids')
    def _get_oldest_model_cache_time(self):
        for cache in self:
            pos_model_cache = self.env['pos.model.cache']
            oldest_cache = pos_model_cache.search([('config_id', '=', cache.id)], order='write_date', limit=1)
            cache.model_oldest_cache_time = oldest_cache.write_date

    model_cache_ids = fields.One2many('pos.model.cache', 'config_id')
    model_oldest_cache_time = fields.Datetime(compute='_get_oldest_model_cache_time', string='Oldest model cache time',
                                              readonly=True)

    def delete_model_cache(self):
        # throw away the old caches
        self.model_cache_ids.unlink()

    def delete_cache(self):
        super(pos_config).delete_cache()
        self.delete_model_cache()
