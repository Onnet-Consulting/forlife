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
            if rec.line_ids:
                update_vals = []
                for line in rec.line_ids:

                    # code Thuế GTGT được khấu trừ của hàng hoá
                    # account_tax = self.env['account.account'].search(
                    #     [('code', '=', '1331000001'), ('company_id', '=', line.company_id.id)])
                    # # Phải trả người bán mua hàng hóa trong nước
                    # account_pay = self.env['account.account'].search(
                    #     [('code', '=', '3311100001'), ('company_id', '=', line.company_id.id)])
                    #thay the ban ghi
                    if line.product_id and line.display_type == 'product':
                        #  code trung gian nhap kho
                        account = self.env['account.account'].search(
                            [('code', '=', '3319000001'), ('company_id', '=', line.company_id.id)])

                        if rec.invoice_type == 'increase':
                            debit = line.price_total
                            credit = int(0)
                        elif rec.invoice_type == 'decrease':
                            debit = int(0)
                            credit = line.price_total
                        # sql = f"update account_move_line set account_id = {account.id}, name = '{line.product_id.name}', debit = {price}, credit = {credit} where id = {line.id.origin}"
                        # self._cr.execute(sql)

                        # update_vals.append((
                        #     1, line.id.origin, {
                        #         'account_id': account.id,
                        #         'name': line.product_id.name,
                        #         'debit': price,
                        #         'credit': credit
                        #     }
                        # ))
                        # line.update({
                        #     'account_id': account.id,
                        #     'name': line.product_id.name,
                        #     'debit': debit,
                        #     'credit': credit
                        # })

                    elif line.display_type == 'payment_term':
                        if rec.invoice_type == 'increase':
                            debit = int(0)
                            credit = abs(line.amount_currency)
                            balance = -abs(line.balance)
                            amount_currency = -line.amount_currency
                            amount_residual = -line.amount_residual
                            amount_residual_currency = -line.amount_residual_currency
                        elif rec.invoice_type == 'decrease':
                            debit = abs(line.amount_currency)
                            credit = int(0),
                            balance = abs(line.balance)
                            amount_currency = abs(line.amount_currency)
                            amount_residual = abs(line.amount_residual)
                            amount_residual_currency = abs(line.amount_residual_currency)

                        # line.update({
                            # 'debit': debit,
                            # 'credit': credit
                            # 'balance': int(balance),
                            # 'amount_currency': int(amount_currency),
                            # 'amount_residual': int(amount_residual),
                            # 'amount_residual_currency': int(amount_residual_currency)
                        # })
                    #     sql = f"update account_move_line set debit = {price}, credit = {credit} where id = {line.id.origin}"
                    #     self._cr.execute(sql)

                        # update_vals.append((
                        #     1, line.id.origin, {
                        #         'name': line.product_id.name,
                        #         # 'debit': price,
                        #         # 'credit': credit
                        #     }
                        # ))

                # rec.write({
                #     'line_ids': update_vals
                # })

