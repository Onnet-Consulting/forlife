# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, \
    BravoMany2oneField, BravoIntegerField, BravoDecimalField


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'bravo.header.model']

    br1 = BravoMany2oneField('res.company', odoo_name='company_id', bravo_name='BranchCode', field_detail='id')
    br2 = BravoIntegerField(odoo_name='id', bravo_name='Stt')
    br3 = BravoCharField(bravo_name="DocCode", bravo_default='H2')
    br4 = BravoDateField(bravo_name="DocDate", odoo_name="date_order")
    br5 = BravoMany2oneField('res.partner', bravo_name="CustomerCode", odoo_name="partner_id", field_detail="name")


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'bravo.line.model']
    _bravo_table = 'B30AccDocSales'
    _bravo_header = 'sale.order'
    _bravo_header_field = 'order_id'

    br1 = BravoMany2oneField('sale.order', bravo_name='Stt', odoo_name='order_id', field_detail='id', identity=True)
    br2 = BravoIntegerField(bravo_name='BuiltinOrder', odoo_name='id', identity=True)
    br3 = BravoMany2oneField('product.product', bravo_name='ItemCode', odoo_name='product_id', field_detail='barcode')
    br4 = BravoMany2oneField('product.product', bravo_name='ItemName', odoo_name='product_id', field_detail='display_name')
    br5 = BravoDecimalField(bravo_name='UnitPrice', odoo_name='price_unit')
