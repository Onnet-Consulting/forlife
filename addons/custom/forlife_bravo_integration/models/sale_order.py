# -*- coding:utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'bravo.header.model']


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'bravo.line.model']
    _bravo_header = 'sale.order'

