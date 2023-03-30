# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
from odoo.osv.expression import AND
from dateutil.relativedelta import relativedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    brand_id = fields.Many2one('res.brand', string='Brand')

    @api.model
    def search_change_order_ids(self, config_id, brand_id, store_id, domain, limit, offset, search_details):
        """Search for all orders that satisfy the given domain, limit and offset."""
        store_id = self.env['store'].sudo().search([('id', '=', store_id)], limit=1)
        default_domain = [('brand_id', '=', brand_id), '!', '|', ('state', '=', 'draft'), ('state', '=', 'cancelled')]
        if store_id.number_month != 0 and search_details.get('fieldName', False) == 'PHONE':
            start_date = fields.Date.today() - relativedelta(months=store_id.number_month)
            end_date = fields.Date.today()
            default_domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)] + default_domain

        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    @api.model
    def search_refund_order_ids(self, config_id, brand_id, store_id, domain, limit, offset, search_details):
        """Search for all orders that satisfy the given domain, limit and offset."""
        store_id = self.env['store'].sudo().search([('id', '=', store_id)], limit=1)
        default_domain = [('brand_id', '=', brand_id), ('config_id.store_id', '=', store_id.id), '!', '|', ('state', '=', 'draft'), ('state', '=', 'cancelled')]
        if store_id.number_month != 0 and search_details.get('fieldName', False) == 'PHONE':
            start_date = fields.Date.today() - relativedelta(months=store_id.number_month)
            end_date = fields.Date.today()
            default_domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)] + default_domain

        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    # Update brand in POS Order
    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        if pos_id:
            order = order['data']
            pos_session = self.env['pos.session'].browse(order['pos_session_id'])
            brand_id = pos_session.config_id.store_id.brand_id
            if not existing_order:
                pos = self.env['pos.order'].browse(pos_id)
            else:
                pos = existing_order
            for pos_order_id in pos:
                if pos_order_id.brand_id.id != brand_id.id:
                    pos_order_id.brand_id = brand_id
        return pos_id
