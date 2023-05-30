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
    source_record = fields.Boolean(string="Đơn hàng từ nhanh", default=False)
    code_coupon = fields.Char(string="Mã coupon")
    name_customer = fields.Char(string='Tên khách hàng mới')
    note_customer = fields.Text(string='Ghi chú khách hàng')
    order_partner_id = fields.Many2one('res.partner', 'Khách Order')
    carrier_name = fields.Char('Carrier Name')

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if 'state' in vals and rec.nhanh_id:

                self.synchronized_price_nhanh(rec.state, rec)
        return res

    def synchronized_price_nhanh(self, odoo_st, rec):
        status = 'Confirming'
        if odoo_st == 'draft':
            status = 'Confirmed'
        elif odoo_st == 'send':
            status = 'Confirming'
        elif odoo_st == 'sale':
            status = 'Confirmed'
        elif odoo_st == 'done':
            status = 'Success'
        elif odoo_st == 'cancel':
            status = 'Canceled'
        try:
            res_server = constant.get_post_status(self, status, rec)
        except Exception as ex:
            _logger.info(f'Get orders from NhanhVn error {ex}')
            return False
        return True


class SaleOrderLineNhanh(models.Model):
    _inherit = 'sale.order.line'

    discount_price_unit = fields.Float('Đơn giá giảm', compute="_compute_discount_price_unit")
    odoo_price_unit = fields.Float('Đơn giá (Odoo)', compute="_compute_odoo_price_unit")

    def _compute_discount_price_unit(self):
        for item in self:
            item.discount_price_unit = item.x_cart_discount_fixed_price > 0 and item.x_cart_discount_fixed_price / item.product_uom_qty or 0

    def _compute_odoo_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            # if line.qty_invoiced > 0:
            #     continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.odoo_price_unit = 0.0
            else:
                price = line.with_company(line.company_id)._get_display_price()
                line.odoo_price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )