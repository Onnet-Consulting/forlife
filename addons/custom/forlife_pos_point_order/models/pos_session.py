from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        res = super(PosSession, self)._loader_params_res_partner()
        data = res['search_params']['fields']
        data.append('total_points_available_forlife')
        data.append('total_points_available_format')
        res['search_params']['fields'] = data
        return res

    @api.model
    def loader_data_res_partner_from_ui(self, data):
        partner_update = self.env['res.partner'].sudo().search([('id', '=', data[0])])
        return {
            'total_points_available_forlife': partner_update.total_points_available_forlife,
            'total_points_available_format': partner_update.total_points_available_format
        }

    # CONTINUE CHECK BALACE WITH POINT TO CLOSE SESSION, WILL BE CREATE LINE BALANCE IN THE FEATURE TO FIX

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self.ensure_one()
        sudo = self.user_has_groups('point_of_sale.group_pos_user')
        if self.order_ids or self.statement_line_ids:
            self.cash_real_transaction = sum(self.statement_line_ids.mapped('amount'))
            if self.state == 'closed':
                raise UserError(_('This session is already closed.'))
            self._check_if_no_draft_orders()
            self._check_invoices_are_posted()
            cash_difference_before_statements = self.cash_register_difference
            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
                self.order_ids.filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)
            try:
                with self.env.cr.savepoint():
                    data = self.with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
            except AccessError as e:
                if sudo:
                    data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                else:
                    raise e

            try:
                # balance = sum(self.move_id.line_ids.mapped('balance'))
                # with self.move_id._check_balanced({'records': self.move_id.sudo()}):
                pass
            except UserError:
                # Creating the account move is just part of a big database transaction
                # when closing a session. There are other database changes that will happen
                # before attempting to create the account move, such as, creating the picking
                # records.
                # We don't, however, want them to be committed when the account move creation
                # failed; therefore, we need to roll back this transaction before showing the
                # close session wizard.
                self.env.cr.rollback()
                return self._close_session_action(balance)

            self.sudo()._post_statement_difference(cash_difference_before_statements)
            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
                # Set the uninvoiced orders' state to 'done'
                self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
            else:
                self.move_id.sudo().unlink()
            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference)

        self.write({'state': 'closed'})
        return True

