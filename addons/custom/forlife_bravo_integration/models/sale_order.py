# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoIntegerField


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'bravo.header.model']

    br1 = BravoMany2oneField(odoo_name='company_id', bravo_name='BranchCode', field_detail='id')
    br2 = BravoCharField(bravo_name="DocCode", bravo_default='H2')
    br3 = BravoDateField(bravo_name="DocDate", odoo_name="date_order")
    br4 = BravoMany2oneField(bravo_name="CustomerCode", odoo_name="partner_id", field_detail="ref")


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'bravo.line.model']
    _bravo_table = 'B30AccDocSales'
    _bravo_header = 'sale.order'
    _bravo_header_field = 'order_id'

    br1 = BravoMany2oneField(bravo_name='Stt', odoo_name='order_id', field_detail='id', identity=True)
    br2 = BravoIntegerField(bravo_name='BuiltinOrder', odoo_name='id', identity=True)
    br3 = BravoMany2oneField(bravo_name='ItemCode', odoo_name='product_id', field_detail='barcode')
    br4 = BravoMany2oneField(bravo_name='ItemName', odoo_name='product_id', field_detail='display_name')
