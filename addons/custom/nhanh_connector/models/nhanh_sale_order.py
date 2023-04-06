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
    code_coupon = fields.Char(string="Code coupon")
    name_customer = fields.Char(string='Name Customer')

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if 'state' in vals and rec.nhanh_id:

                self.synchronized_price_nhanh(rec.state)
        return res

    def synchronized_price_nhanh(self, odoo_st):
        status = 'Confirming'
        if odoo_st == 'draft':
            status = 'confirmed'
        elif odoo_st == 'send':
            status = 'confirming'
        elif odoo_st == 'sale':
            status = 'confirmed'
        elif odoo_st == 'done':
            status = 'success'
        elif odoo_st == 'cancel':
            status = 'canceled'
        try:
            res_server = constant.get_post_status(self, status)
        except Exception as ex:
            _logger.info(f'Get orders from NhanhVn error {ex}')
            return False
        return True


class SaleOrderLineNhanh(models.Model):
    _inherit = 'sale.order.line'
