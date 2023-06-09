from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)

    def button_popup_increase_decrease_invoice(self):

        return {
            'name': 'increase decrease invoice',
            'domain': [],
            'res_model': 'wizard.increase.decrease.invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_origin_invoice_id': self.id},
            'target': 'new',
        }


    # @api.onchange('invoice_type')
    # def onchange_view_invoice_type(self):
    #     for rec in self:
    #         if rec.line_ids and rec.invoice_type:
    #             account_tax = self.env['account.account'].search([('code', '=', '1331000001'), ('company_id', '=', rec.company_id.id)])
    #
    #
    #             for line in rec.line_ids:
    #                 #thay the ban ghi
    #                 if line.product_id and line.display_type == 'product':
    #                     #  code trung gian nhap kho .partner_id.property_account_payable_id
    #                     account_id = line.product_id.categ_id.property_stock_account_input_categ_id
    #
    #                     debit = abs(line.debit - line.credit) if rec.invoice_type == 'increase' else int(0)
    #                     credit = int(0) if rec.invoice_type == 'increase' else abs(line.debit - line.credit)
    #                     balance = debit - credit
    #                     line.update({
    #                         'account_id': account_id.id,
    #                         'name': line.product_id.name,
    #                         'debit': int(debit),
    #                         'credit': int(credit),
    #                         'balance': balance
    #                     })
    #
    #                 elif line.display_type == 'payment_term':
    #                     debit = int(0) if rec.invoice_type == 'increase' else int(abs(line.amount_currency))
    #                     credit = int(abs(line.amount_currency)) if rec.invoice_type == 'increase' else int(0)
    #                     balance = debit - credit
    #                     line.update({
    #                         'debit': int(debit),
    #                         'credit': int(credit),
    #                         'balance': balance
    #                     })
    #
    #                 elif line.display_type == 'tax':
    #                     debit = abs(line.debit - line.credit) if rec.invoice_type == 'increase' else int(0)
    #                     credit = int(0) if rec.invoice_type == 'increase' else abs(line.debit - line.credit)
    #                     balance = debit - credit
    #                     line.update({
    #                         # 'account_id': account_tax.id,
    #                         'debit': int(debit),
    #                         'credit': int(credit),
    #                         'balance': balance
    #                     })
    #
    #         if rec.invoice_type == 'decrease':
    #             self.env.context = self.with_context(noonchange=True).env.context
