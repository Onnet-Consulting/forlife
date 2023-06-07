from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'


    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)

    def button_increase_decrease_invoice(self, default=None):

        self.ensure_one()
        default = dict(default or {})
        default.update({
            'invoice_type': False,
            # 'move_type': 'entry',
            'origin_invoice_id': self.id
        })
        move_copy_id = self.copy(default)
        move_copy_id.move_type = 'entry'

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
            if rec.line_ids and rec.invoice_type:
                account = self.env['account.account'].search([('code', '=', '3319000001'), ('company_id', '=', rec.company_id.id)])
                account_tax = self.env['account.account'].search([('code', '=', '1331000001'), ('company_id', '=', rec.company_id.id)])
                for line in rec.line_ids:
                    #thay the ban ghi
                    if line.product_id and line.display_type == 'product':
                        #  code trung gian nhap kho
                        debit = abs(line.debit - line.credit) if rec.invoice_type == 'increase' else int(0)
                        credit = int(0) if rec.invoice_type == 'increase' else abs(line.debit - line.credit)
                        balance = debit - credit
                        line.update({
                            'account_id': account.id,
                            'name': line.product_id.name,
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': balance
                        })

                    elif line.display_type == 'payment_term':
                        debit = int(0) if rec.invoice_type == 'increase' else int(abs(line.amount_currency))
                        credit = int(abs(line.amount_currency)) if rec.invoice_type == 'increase' else int(0)
                        balance = debit - credit
                        line.update({
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': balance
                        })

                    elif line.display_type == 'tax':
                        debit = abs(line.debit - line.credit) if rec.invoice_type == 'increase' else int(0)
                        credit = int(0) if rec.invoice_type == 'increase' else abs(line.debit - line.credit)
                        balance = debit - credit
                        line.update({
                            'account_id': account_tax.id,
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': balance
                        })
