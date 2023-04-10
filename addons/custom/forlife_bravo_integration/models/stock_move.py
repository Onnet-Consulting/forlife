# -*- coding:utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'mssql.server']

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self.filtered(lambda m: m.state == 'done'):
            pass
        return res

    def get_purchase_picking_data(self):
        bravo_table = 'B30AccDocPurchase'
        moves = self.filtered(lambda m: m.purchase_line_id and m.account_move_ids)
        for idx,move in enumerate(moves, start=1):
            picking = move.picking_id
            picking_data = picking.read(['id', 'name', 'date_done'])
            picking_partner= picking.partner_id
            account_move = move.account_move_ids[0]
            bravo_data = {
                'CompanyCode': picking.company_id.code,
                'Stt': picking_data.id,
                'DocCode': 'NK' if picking_partner.group_id == self.env.ref('forlife_pos_app_member.partner_group_1') else 'NM',
                'DocNo': picking.name,
                'DocDate': move.date,
                'CustomerCode': picking_partner.ref,
                'CustomerName': picking_partner.name,
                'Address': picking_partner.contact_address_complete,
                'EmployeeCode': picking.user_id.employee_id.code,
                'BuiltinOrder': idx
            }
            for acl in account_move:
                pass

