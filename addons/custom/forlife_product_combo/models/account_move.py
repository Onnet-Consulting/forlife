from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'


    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')

    def button_increase_decrease_invoice(self, default=None):

        self.ensure_one()
        default = dict(default or {})
        default['invoice_type'] = 'increase'
        move_copy_id = self.copy(default)

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'res_id': move_copy_id.id,
        }


    @api.onchange('invoice_type')
    def onchange_view_invoice_type(self):
        for rec in self:
            if rec.invoice_type == 'increase':
                abc = 'tang gia tri'

            if rec.invoice_type == 'decrease':
                abc = 'giam gia tri'
            if rec.line_ids:
                for line in rec.line_ids:
                    #  code trung gian nhap kho
                    account = self.env['account.account'].search([('code', '=', '3319000001'), ('company_id', '=', line.company_id.id)])
                    # code Thuế GTGT được khấu trừ của hàng hoá
                    account_tax = self.env['account.account'].search(
                        [('code', '=', '1331000001'), ('company_id', '=', line.company_id.id)])
                    # Phải trả người bán mua hàng hóa trong nước
                    account_pay = self.env['account.account'].search(
                        [('code', '=', '3311100001'), ('company_id', '=', line.company_id.id)])
                    #thay the ban ghi
                    if line.product_id and line.display_type == 'product':
                        if rec.invoice_type == 'increase':
                            price = line.price_total
                            credit = 0
                        if rec.invoice_type == 'decrease':
                            price = 0
                            credit = line.price_total

                        line.write({
                            'account_id': account.id,
                            'name': line.product_id.name,
                            'debit': price,
                            'credit': credit
                        })

                    # if line.display_type == 'tax':
                    #     line.write({
                    #         'account_id': account_tax.id
                    #     })

                    # if line.display_type == 'payment_term':
                    #     if rec.invoice_type == 'increase':
                    #         price_payment_term = line.debit
                    #         credit_payment_term = line.credit
                    #     if rec.invoice_type == 'decrease':
                    #         price_payment_term = line.credit
                    #         credit_payment_term = line.debit
                    #
                    #     line.write({
                    #         'account_id': account_pay.id,
                    #         'debit': price_payment_term,
                    #         'credit': credit_payment_term
                    #     })

