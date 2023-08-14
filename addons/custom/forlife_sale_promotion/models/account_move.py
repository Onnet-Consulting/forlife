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

        return action

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
                    
                account_tax = pr.product_id.taxes_id.filtered(lambda x: x.company_id.id == self.env.company.id)
                account_repartition_tax = account_tax and account_tax[0].invoice_repartition_line_ids.filtered(lambda p: p.repartition_type == 'tax')
                
                if pr.promotion_type in ['vip_amount', 'reward']:
                    line_allow = True
                    account_debit_id = pr.value > 0 and pr.account_id or property_account_receivable_id
                    account_credit_id = pr.value > 0 and property_account_receivable_id or pr.account_id

                if pr.promotion_type == 'customer_shipping_fee':
                    line_allow = True
                    account_debit_id = property_account_receivable_id
                    account_credit_id = pr.account_id
                if pr.promotion_type == 'nhanh_shipping_fee':
                    line_allow = True
                    account_debit_id = pr.account_id
                    account_credit_id = account_payable_customer_id

                # cho phép tạo bút toán với các promotion type
                if line_allow:
                    account_tax = pr.product_id.taxes_id.filtered(lambda x: x.company_id.id == self.env.company.id)
                    account_tax_id = False
                    product_with_tax_value = abs(pr.value)
                    product_value_without_tax = abs(pr.value)
                    product_tax_value = 0
                    # check thue
                    if account_tax and len(account_tax):
                        account_tax_ids = account_tax[0].invoice_repartition_line_ids.filtered(lambda p: p.repartition_type == 'tax')
                        if len(account_tax_ids) and account_tax_ids[0].account_id:
                            account_tax_id = account_tax_ids[0].account_id
                            product_value_without_tax = round(account_tax_id and ((product_with_tax_value * 100) / (account_tax[0].amount + 100)), 0)
                            product_tax_value = product_with_tax_value - product_value_without_tax

                    line_ids.append({
                        'name': self.name + "(%s)" % pr.description,
                        'product_id': pr.product_id.id,
                        'account_id': account_debit_id and account_debit_id.id,
                        'analytic_account_id': pr.analytic_account_id.id,
                        'partner_id': pr.partner_id.id if pr.promotion_type == 'customer_shipping_fee' else self.partner_id.id,
                        'debit': product_value_without_tax,
                        'credit': 0
                    })
                    line_ids.append({
                        'name': self.name + "(%s)" % pr.description,
                        'product_id': pr.product_id.id,
                        'account_id': account_credit_id and account_credit_id.id,
                        'analytic_account_id': pr.analytic_account_id.id,
                        'partner_id': pr.partner_id.id if pr.promotion_type == 'customer_shipping_fee' else self.partner_id.id,
                        'debit': 0,
                        'credit': product_value_without_tax
                    })
                    if pr.promotion_type == 'customer_shipping_fee':
                        if not account_repartition_tax or not account_repartition_tax[0].account_id:
                            raise UserError("Chưa cấu hình tài khoản thuế cho sản phầm!")

                    # có thế thì tạo bút toán cho thuế
                    if account_tax_id:
                        line_ids.append({
                            'name': self.name + "(%s)" % pr.description,
                            'product_id': pr.product_id.id,
                            'account_id': self.partner_id.property_account_receivable_id.id,
                            'analytic_account_id': pr.analytic_account_id.id,
                            'debit': 0,
                            'credit': pr.value > 0 and product_tax_value or -product_tax_value
                        })
                        line_ids.append({
                            'name': self.name + "(%s)" % pr.description,
                            'product_id': pr.product_id.id,
                            'account_id': account_tax_id and account_tax_id.id,
                            'analytic_account_id': pr.analytic_account_id.id,
                            'debit': pr.value > 0 and product_tax_value or -product_tax_value,
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
            # set tài khoản tương ứng khi tạo hóa đơn từ đơn hàng
            super(AccountMoveLine, line)._compute_account_id()
            product_lines = self.filtered(lambda line: line.display_type == 'product' and line.move_id.is_invoice(True))
            for line in product_lines:
                if line.product_id:
                    sale_line_id = line.sale_line_ids
                    order_id = sale_line_id.order_id
                    income_online_account_id = line.with_company(line.company_id).product_id.categ_id.income_online_account_id
                    income_sale_account_id = line.with_company(line.company_id).product_id.categ_id.income_sale_account_id
                    if not sale_line_id.x_free_good:
                        if order_id.x_sale_chanel == "online" and income_online_account_id:
                            line.account_id = income_online_account_id or line.account_id
                        elif order_id.x_sale_chanel == "wholesale" and income_sale_account_id:
                            line.account_id = income_sale_account_id or line.account_id
