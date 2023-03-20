# -*- coding: utf-8 -*-
from odoo.addons.nhanh_connector.models import constant
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)

class SaleOrderNhanh(models.Model):
    _inherit = 'sale.order'

    nhanh_id = fields.Integer(string='Id Nhanh.vn')
    numb_action_confirm = fields.Integer(default=0)
    source_record = fields.Boolean(string="From nhanh", default=False)



class SaleOrderLineNhanh(models.Model):
    _inherit = 'sale.order.line'
