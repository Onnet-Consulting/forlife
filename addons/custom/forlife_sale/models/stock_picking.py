# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

class StockMove(models.Model):
    _inherit = 'stock.move'

    x_scheduled_date = fields.Date(string='Ngày giao hàng dự kiến')
