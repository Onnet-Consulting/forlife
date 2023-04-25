# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_open_quant_period(self):
        self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = {
            'name': _('Inventory Period'),
            'view_mode': 'list',
            'view_id': self.env.ref('forlife_stock_report.stock_quant_period_view_tree').id,
            'res_model': 'stock.quant.period',
            'type': 'ir.actions.act_window',
            'domain': [('product_id', 'in', self.ids)],
        }
        return action
