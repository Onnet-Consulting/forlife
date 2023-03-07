# -*- coding:utf-8 -*-

from odoo import api, fields, models
from ..fields import BravoField, BravoCharField, BravoDatetimeField, BravoDateField, \
    BravoMany2oneField, BravoIntegerField, BravoDecimalField
from odoo.exceptions import ValidationError


class PurchaseAccountMoveLine(models.TransientModel):
    _name = 'bravo.purchase.account.move'
    _bravo_table = 'B30AccDocPurchase'

    account_move_id = fields.Many2one('account.move', required=True)

    def read_insert_bravo_data(self):
        self.ensure_one()
        move_id = self.account_move_id
        partner = self.account_move_id.partner_id
        header_data = {
            "BranchCode": move_id.company_id.code,
            "Stt": move_id.id,
            "DocNo": move_id.stock_move_id.picking_id.name,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Description": move_id.narration
        }
        line_data = []
        for line in move_id.line_ids:
            pass

