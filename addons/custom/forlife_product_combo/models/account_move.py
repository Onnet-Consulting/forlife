from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)

    def _post(self, soft=True):
        for record in self:
            if record.origin_invoice_id:
                record.amount_total = abs(record.amount_total)
        return super(AccountMove, self)._post(soft)

    def _get_unbalanced_moves(self, container):
        if self.origin_invoice_id:
            return []
        else:
            return super(AccountMove, self)._get_unbalanced_moves(container)

    def button_increase_decrease_invoice(self, default=None):

        self.ensure_one()
        default = dict(default or {})
        default.update({
            'invoice_type': False,
            # 'move_type': 'in_invoice',
            'origin_invoice_id': self.id
        })
        move_copy_id = self.copy(default)
        # move_copy_id.move_type = 'entry'

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
            if rec.invoice_type == 'decrease':
                self.env.context = self.with_context(noonchange=True).env.context

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('balance', 'move_id.is_storno')
    def _compute_debit_credit(self):
        if self.move_id[0].invoice_type == 'decrease' and self.move_id[0].origin_invoice_id and not self.env.context.get('noonchange'):
            for line in self:
                if abs(line.debit - line.credit) != abs(line.balance):
                    if line.display_type in ['product', 'tax']:
                        debit = -line.balance if line.balance < 0.0 else 0.0
                        credit = line.balance if line.balance > 0.0 else 0.0
                        self.env.context = self.with_context(noonchange=True).env.context
                        line.update({
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': debit - credit
                        })
                    else:
                        debit = line.balance if line.balance > 0.0 else 0.0
                        credit = -line.balance if line.balance < 0.0 else 0.0
                        self.env.context = self.with_context(noonchange=True).env.context
                        line.update({
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': debit - credit
                        })
                elif abs(line.debit - line.credit) == abs(line.balance):
                    if line.display_type in ['product', 'tax']:
                        debit = line.balance if line.balance > 0.0 else 0.0
                        credit = -line.balance if line.balance < 0.0 else 0.0
                        self.env.context = self.with_context(noonchange=True).env.context
                        line.update({
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': debit - credit
                        })
                    else:
                        debit = -line.balance if line.balance < 0.0 else 0.0
                        credit = line.balance if line.balance > 0.0 else 0.0
                        self.env.context = self.with_context(noonchange=True).env.context
                        line.update({
                            'debit': int(debit),
                            'credit': int(credit),
                            'balance': debit - credit
                        })

        else:
            if self.move_id[0].invoice_type != 'decrease' and not self.env.context.get('noonchange'):
                return super(AccountMoveLine, self)._compute_debit_credit()
        return True