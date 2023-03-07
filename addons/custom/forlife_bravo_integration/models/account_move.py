# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField, BravoCharField, BravoDatetimeField, BravoDateField, \
    BravoMany2oneField, BravoIntegerField, BravoDecimalField
from odoo.exceptions import ValidationError


class PurchaseAccountMoveLine(models.TransientModel):
    _name = 'purchase.account.move.line'
    _inherit = 'bravo.model'
    _bravo_table = 'xyz'

    line_id = fields.Many2one('account.move.line', required=True)
    move_id = fields.Many2one('account.move', related='line_id.move_id', store=True)
    br1 = BravoMany2oneField('account.move', bravo_name='BranchCode', odoo_name='move_id',
                             field_detail='company_id.name')
    br2 = BravoMany2oneField('account.move', bravo_name='CustomerName', odoo_name='move_id',
                             field_detail='partner_id.ref')


    def get_insert_sql(self):
        pass