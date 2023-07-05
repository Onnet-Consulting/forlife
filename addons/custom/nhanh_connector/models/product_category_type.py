# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductCategoryType(models.Model):
    _inherit = 'product.category.type'

    # tuuh
    x_sync_nhanh = fields.Boolean('Đồng bộ lên nhanh')
