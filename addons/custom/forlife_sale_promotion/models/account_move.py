# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('display_type', 'company_id')
    def _compute_account_id(self):
        for line in self:
            super(AccountMoveLine, line)._compute_account_id()
            product_lines = self.filtered(lambda line: line.display_type == 'product' and line.move_id.is_invoice(True))
            for line in product_lines:
                if line.product_id:
                    sale_line_id = line.sale_line_ids
                    order_id = sale_line_id.order_id
                    income_online_account_id = line.product_id.categ_id.income_online_account_id
                    income_sale_account_id = line.product_id.categ_id.income_sale_account_id
                    if not sale_line_id.x_free_good:
                        if order_id.x_sale_chanel == "online" and income_online_account_id:
                            line.account_id = income_online_account_id or line.account_id
                        elif order_id.x_sale_chanel == "wholesale" and income_sale_account_id:
                            line.account_id = income_sale_account_id or line.account_id
