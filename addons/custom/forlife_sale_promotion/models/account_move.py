# -*- coding: utf-8 -*-
from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    promotion_ids = fields.One2many('account.move.promotion', 'move_id', string="Promotion")
    promotion_journal_count = fields.Integer(string="Promotion journal count")

    def action_view_promotion_journal(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        # if len(source_orders) > 1:
        #     result['domain'] = [('id', 'in', source_orders.ids)]
        # elif len(source_orders) == 1:
        #     result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
        #     result['res_id'] = source_orders.idF
        # else:
        #     result = {'type': 'ir.actions.act_window_close'}
        return result