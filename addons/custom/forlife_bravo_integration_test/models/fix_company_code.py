# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.forlife_bravo_integration.fields import *


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    br3 = BravoCharField(bravo_name='CompanyCode', bravo_default='test')


class OccasionCode(models.Model):
    _inherit = 'occasion.code'

    br3 = BravoCharField(bravo_name='CompanyCode', bravo_default='test')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    br3 = BravoCharField(bravo_name='CompanyCode', bravo_default='test')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    br3 = BravoCharField(bravo_name='CompanyCode', bravo_default='test')


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    br3 = BravoCharField(bravo_name='CompanyCode', bravo_default='test')
