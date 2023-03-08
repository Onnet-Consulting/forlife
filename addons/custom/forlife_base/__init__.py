# -*- coding: utf-8 -*-

from . import models
from odoo.api import Environment, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    category_ids = env['product.category'].search([('parent_id', '=', False)])
    category_ids._compute_category_code()
