from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        all_pos = self.env['pos.config'].search([('store_id', '=', self.config_id.store_id.id), ('id', '!=', self.config_id.id)])
        branchs = self.config_id.store_id.brand_id
        pos_expense_labels = self.env['pos.expense.label'].search([])
        pos = [{
            'id': r.id,
            'name': r.name
        } for r in all_pos]
        branch = [{
            'id': r.id,
            'name': r.name
        } for r in branchs]
        labels = [{'id': r.id, 'name': r.display_name} for r in pos_expense_labels]
        loaded_data.update({
            'pos.customize': pos,
            'pos.branch': branch,
            'pos.expense.label': labels,
        })
        return loaded_data

    @api.model
    def _pos_ui_models_to_load(self):
        models_to_load = super(PosSession, self)._pos_ui_models_to_load()
        models_to_load.append('account.bank.statement.line')
        return models_to_load

    def _loader_params_account_bank_statement_line(self):
        query = """select id from account_bank_statement_line where pos_session_id in
        (select id from pos_session where config_id in
        (select id as pos from pos_config where store_id = {}) and state = 'opened')
        and is_reference = False and pos_session_id != {};
                                                """.format(self.config_id.store_id.id, self.id)
        self.env.cr.execute(query)
        statement_lines_pos = self.env.cr.fetchall()
        return {'search_params': {
            'domain': [('id', 'in', statement_lines_pos)],
            'fields': ['name', 'move_id', 'amount', 'pos_config_id', 'to_store_tranfer']}
        }

    def _get_pos_ui_account_bank_statement_line(self, params):
        return self.env['account.bank.statement.line'].search_read(**params['search_params'])

    def load_new_bank_statements(self):
        model_name = 'account_bank_statement_line'
        loader = getattr(self, '_get_pos_ui_%s' % model_name, None)
        params = getattr(self, '_loader_params_%s' % model_name, None)
        if loader and params:
            return loader(params())
        else:
            raise NotImplementedError(_("The function to load %s has not been implemented.", model_name))

    def create_pos_transfer_journal_entry(self, _type, amount, reason, extras):
        self.ensure_one()
        balance = amount if _type == 'out' else -amount
        move_val = {
            'ref': self.name + ' ' + reason or '',
            'move_type': 'entry',
            'pos_transfer_cash_2office': True,
            'pos_orig_amount': balance,
            'pos_trans_session_id': self.id,
            'narration': self.name + reason or '',
            'currency_id': self.currency_id.id,
            'partner_id': self.config_id.store_id.contact_id.id,
            'company_id': self.company_id.id,
        }
        if self.config_id.store_id.receipt_expense_journal_id:
            move_val['journal_id'] = self.config_id.store_id.receipt_expense_journal_id.id
        liquidity_line_vals = {
            'name': _('Transfer POS-Office: %s') % self.name + ' ' + reason or '',
            'partner_id': self.config_id.store_id.contact_id.id,
            'account_id': self.config_id.store_id.default_office_cash_account_id.id,
            'currency_id': self.currency_id.id,
            'debit': balance > 0 and balance or 0.0,
            'credit': balance < 0 and -balance or 0.0,
        }
        # Create the counterpart line values.
        counterpart_line_vals = {
            'name': _('Counterpart Transfer POS-Office: %s') % self.name + ' ' + reason or '',
            'account_id': self.config_id.store_id.account_intermediary_pos.id,
            'partner_id': self.config_id.store_id.contact_id.id,
            'currency_id': self.currency_id.id,
            'debit': -balance if balance < 0.0 else 0.0,
            'credit': balance if balance > 0.0 else 0.0,
        }
        move_val['line_ids'] = [
            (0, 0, liquidity_line_vals),
            (0, 0, counterpart_line_vals)]
        move = self.env['account.move'].create(move_val)
        return move

    def try_cash_in_out(self, _type, amount, reason, extras):
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session"))
        payment_ref = ''
        expense = self.env['pos.expense.label']
        if extras['type_tranfer'] == 4 and extras['expense_label']:
            expense = self.env['pos.expense.label'].browse(extras['expense_label'])
            payment_ref = ' '.join([s.name for s in sessions]) + ': ' + expense.display_name if expense else ''

        account_bank_st_line = self.env['account.bank.statement.line'].create([
            {
                'pos_session_id': session.id,
                'journal_id': session.cash_journal_id.id,
                'amount': sign * amount,
                'date': fields.Date.context_today(self),
                'payment_ref': payment_ref or '-'.join([session.name, extras['translatedType'], reason]),
                'to_store_tranfer': extras['shop']
                if 'shop' in extras and _type == 'out' and extras['shop'] and extras['type_tranfer'] == 2 else False,
                'is_reference': True if 'reference' in extras and extras['reference'] else False,
                'pos_transfer_type': str(extras.get('type_tranfer')) if extras.get('type_tranfer') != 0 else False,
                'expense_label_id': expense and expense.id or False
            }
            for session in sessions
        ])
        if 'reference' in extras and extras['reference']:
            statement_line = self.env['account.bank.statement.line'].sudo().search([('id', '=', extras['reference'])])
            if not statement_line.is_reference:
                account_bank_st_line.write({
                    'ref': 'From {}'.format(statement_line.move_id.name),
                    'from_store_tranfer': statement_line.pos_session_id.config_id.id
                })
                statement_line.write({
                    'is_reference': True
                })
            else:
                raise UserError(_('The ticket already in use!'))
        message_content = [f"Cash {extras['translatedType']}", f'- Amount: {extras["formattedAmount"]}']
        if reason:
            message_content.append(f'- Reason: {reason}')
        self.message_post(body='<br/>\n'.join(message_content))

        # Loại: chuyển tiền về văn phòng
        if extras['type_tranfer'] == 1:
            if _type == 'in':
                raise UserError(_('Amount transferred to company must be a negative number and transfer type \'out\''))
            for session in sessions:
                session.create_pos_transfer_journal_entry(_type, amount, reason, extras)
        return True

# [(1, 'Văn phòng'), (2, 'Cửa hàng'), (3, 'Chênh lệch khác'), (4, 'Mua chi phí')]
