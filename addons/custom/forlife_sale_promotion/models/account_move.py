# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    promotion_ids = fields.One2many('account.move.promotion', 'move_id', string="Promotion")
    promotion_journal_count = fields.Integer(string="Promotion journal count",
                                             compute="_compute_promotion_journal_count")
    promotion_move_id = fields.Many2one('account.move')
    promotion_journal_ids = fields.One2many('account.move', 'promotion_move_id', string="Promotion entry")

    @api.depends('promotion_journal_ids')
    def _compute_promotion_journal_count(self):
        for rec in self:
            rec.promotion_journal_count = len(rec.promotion_journal_ids)

    def action_view_promotion_journal(self):
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if self.promotion_journal_count > 1:
            action['domain'] = [('id', 'in', self.promotion_journal_ids.ids)]
        elif self.promotion_journal_count == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = self.promotion_journal_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        # context = {
        #     'default_move_type': 'out_invoice',
        # }
        # if len(self) == 1:
        #     context.update({
        #         'default_partner_id': self.partner_id.id,
        #         'default_partner_shipping_id': self.partner_shipping_id.id,
        #         'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
        #         'default_invoice_origin': self.name,
        #     })
        # action['context'] = context
        return action

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        # if len(source_orders) > 1:
        #     result['domain'] = [('id', 'in', source_orders.ids)]
        # elif len(source_orders) == 1:
        #     result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
        #     result['res_id'] = source_orders.idF
        # else:
        #     result = {'type': 'ir.actions.act_window_close'}
        return result

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.promotion_ids:
            line_ids = []
            journal_id = self.env['account.journal'].search([('is_promotion', '=', True)], limit=1)
            for pr in self.promotion_ids:
                account_debit_id = False
                account_credit_id = False
                line_allow = False
                property_account_receivable_id = self.partner_id.property_account_receivable_id
                if not property_account_receivable_id:
                    raise UserError("Chưa cấu hình tài khoản thu cho khách hàng")

                account_payable_customer_id = self.partner_id.property_account_payable_id
                if not account_payable_customer_id:
                    raise UserError("Chưa cấu hình tài khoản phải trả cho khách hàng")

                account_tax = pr.product_id.taxes_id
                account_repartition_tax = account_tax and account_tax[0].invoice_repartition_line_ids.filtered(lambda p: p.repartition_type == 'tax')

                if pr.promotion_type in ['vip_amount', 'reward']:
                    line_allow = True
                    account_debit_id = pr.value > 0 and pr.account_id or property_account_receivable_id
                    account_credit_id = pr.value > 0 and property_account_receivable_id or pr.account_id

                if pr.promotion_type == 'nhanh_shipping_fee':
                    line_allow = True
                    account_debit_id = property_account_receivable_id
                    account_credit_id = pr.account_id
                if pr.promotion_type == 'customer_shipping_fee':
                    line_allow = True
                    account_debit_id = pr.account_id
                    account_credit_id = account_payable_customer_id

                if line_allow:
                    line_ids.append({
                        'name': self.name + "(%s)" % pr.description,
                        'product_id': pr.product_id.id,
                        'account_id': account_debit_id and account_debit_id.id,
                        'analytic_account_id': pr.analytic_account_id.id,
                        'debit': abs(pr.value),
                        'credit': 0
                    })
                    line_ids.append({
                        'name': self.name + "(%s)" % pr.description,
                        'product_id': pr.product_id.id,
                        'account_id': account_credit_id and account_credit_id.id,
                        'analytic_account_id': pr.analytic_account_id.id,
                        'debit': 0,
                        'credit': abs(pr.value)
                    })
                    if pr.promotion_type == 'nhanh_shipping_fee':
                        if not account_repartition_tax or not account_repartition_tax[0].account_id:
                            raise UserError("Chưa cấu hình tài khoản thuế cho sản phầm!")

                        line_ids.append({
                            'name': self.name + "(%s)" % pr.description,
                            'product_id': pr.product_id.id,
                            'account_id': account_repartition_tax and account_repartition_tax[0].account_id.id,
                            'analytic_account_id': pr.analytic_account_id.id,
                            'debit': 0,
                            'credit': abs(pr.value)
                        })
                        line_ids.append({
                            'name': self.name + "(%s)" % pr.description,
                            'product_id': pr.product_id.id,
                            'account_id': account_repartition_tax and account_repartition_tax[0].account_id.id,
                            'analytic_account_id': pr.analytic_account_id.id,
                            'debit': abs(pr.value),
                            'credit': 0
                        })

            default_value = {
                'date': self.invoice_date,
                'journal_id': journal_id and journal_id.id or (self.journal_id and self.journal_id.id or False),
                'promotion_move_id': self.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, line_id) for line_id in line_ids]
            }
            invoice_id = self.copy(default_value)
            invoice_id.action_post()
        return res


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
