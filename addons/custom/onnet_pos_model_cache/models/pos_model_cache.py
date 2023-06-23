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

    compute_user_id = fields.Many2one('res.users', 'Cache compute user', required=True)
    search_context = fields.Text(string="Search Context")

    @api.model
    def refresh_all_model_caches(self):
        self.env['pos.model.cache'].search([]).refresh_cache()

    @api.model
    def refresh_product_model_caches(self):
        self.env['pos.model.cache'].search([('model', '=', 'product.product')]).refresh_cache()

    @api.model
    def refresh_promotion_model_caches(self):
        self.env['pos.model.cache'].search([('model', '=', 'promotion.pricelist.item')]).refresh_cache()

    def refresh_cache(self):
        for cache in self:
            model_obj = self.env[cache.model].with_user(cache.compute_user_id.id)
            records = model_obj.search(cache.get_model_domain(), order=self.env[cache.model]._order)
            res = records.read(cache.get_model_fields())
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
