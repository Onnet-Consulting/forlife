import pytz
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class InheritPosOrder(models.Model):
    _inherit = 'pos.order'

    real_to_invoice = fields.Boolean(string='Real To Invoice')
    invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='pos_order_id', string='Invoices')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @staticmethod
    def _create_promotion_account_move(order_line):
        display_name = order_line.product_id.get_product_multiline_description_sale()
        name = order_line.product_id.default_code + " " + display_name if order_line.product_id.default_code else display_name
        credit_account = order_line.product_id.product_tmpl_id._get_product_accounts()
        return [
            (0, 0, {
                'is_state_registration': order_line.is_state_registration,
                'pos_order_line_id': order_line.id,
                'product_id': order_line.product_id.id,
                'quantity': order_line.qty,
                'discount': order_line.discount,
                'price_unit': order_line.price_unit,
                'name': name,
                'tax_ids': [(6, 0, order_line.tax_ids_after_fiscal_position.ids)],
                'product_uom_id': order_line.product_uom_id.id,
                'display_type': 'product',
                'account_id': (credit_account['income'] or credit_account['expense']).id or None,
                'credit': order_line.price_unit,
                'debit': 0
            }), (0, 0, {
                'is_state_registration': order_line.is_state_registration,
                'pos_order_line_id': order_line.id,
                'product_id': order_line.product_id.id,
                'quantity': order_line.qty,
                'discount': order_line.discount,
                'price_unit': order_line.price_unit,
                'name': name,
                'tax_ids': [(6, 0, order_line.tax_ids_after_fiscal_position.ids)],
                'product_uom_id': order_line.product_uom_id.id,
                'display_type': 'payment_term',
                'account_id': order_line.order_id.partner_id.property_account_receivable_id.id,
                'credit': 0,
                'debit': order_line.price_unit
            })
        ]

    def create_promotion_account_move(self):
        self.ensure_one()
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        invoice_date = fields.Datetime.now() if self.session_id.state == 'closed' else self.date_order
        values = []
        results = self.env['account.move']
        for line in self.lines:
            if not line.product_id.check_is_promotion():
                continue
            point_promotion = self.env['points.promotion'].sudo().search([('product_discount_id', '=', line.product_id.id)], limit=1)
            if point_promotion:
                journal_id = point_promotion.account_journal_id.id
            else:
                promotion_program = self.env['promotion.program'].sudo().search([('product_discount_id', '=', line.product_id.id)], limit=1)
                if promotion_program:
                    journal_id = promotion_program.journal_id.id
                else:
                    raise ValidationError(_("Cannot found points/program promotion's product %s") % line.product_id.name)

            values.append({
                'invoice_origin': self.name,
                'journal_id': journal_id,
                'pos_order_id': self.id,
                'move_type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
                'ref': self.name,
                'partner_id': self.partner_id.id,
                'partner_bank_id': self._get_partner_bank_id(),
                # considering partner's sale pricelist's currency
                'currency_id': self.pricelist_id.currency_id.id,
                'invoice_user_id': self.user_id.id,
                'invoice_date': invoice_date.astimezone(timezone).date(),
                'fiscal_position_id': self.fiscal_position_id.id,
                'invoice_line_ids': self._create_promotion_account_move(line),
                'invoice_payment_term_id': self.partner_id.property_payment_term_id.id or False,
                'invoice_cash_rounding_id': self.config_id.rounding_method.id
                if self.config_id.cash_rounding and (not self.config_id.only_round_cash_method or any(
                    p.payment_method_id.is_cash_count for p in self.payment_ids))
                else False,
                'narration': self.note or None
            })

        if values:
            results = results.create(values)
            results._post()
        return results

    @api.model
    def _order_fields(self, ui_order):
        for line in ui_order['lines']:
            if line[-1]['product_id']:
                point_promotion = self.env['points.promotion'].sudo().search(
                    [('product_discount_id', '=', line[-1]['product_id'])], limit=1
                )
                line[-1]['is_state_registration'] = point_promotion and point_promotion.check_validity_state_registration() or False
        results = super(InheritPosOrder, self)._order_fields(ui_order)
        results['real_to_invoice'] = ui_order['real_to_invoice']
        return results

    def _prepare_invoice_line(self, order_line):
        if order_line.product_id.check_is_promotion():
            return None
        invoice_line = super(InheritPosOrder, self)._prepare_invoice_line(order_line)
        invoice_line.update({
            'pos_order_line_id': order_line.id,
            'account_analytic_id': self.session_id.config_id.store_id.analytic_account_id.id,
        })
        return invoice_line

    def _prepare_invoice_lines(self):
        return [
            invoice_line
            for invoice_line in super(InheritPosOrder, self)._prepare_invoice_lines()
            if invoice_line[-1]
        ]

    def _prepare_invoice_vals(self):
        result = super(InheritPosOrder, self)._prepare_invoice_vals()
        if self.to_invoice and self.real_to_invoice:
            result.update({'exists_bkav': True, 'is_post_bkav': True})
        result['pos_order_id'] = self.id
        return result

    @api.model
    def _process_order(self, order, draft, existing_order):
        to_invoice = order['data']['to_invoice']
        if not to_invoice:
            store = self.env['pos.session'].sudo().browse(order['data']['pos_session_id']).config_id.store_id
            partner_id = store.contact_id.id
            if not partner_id:
                raise ValidationError(_("Cannot found contact's store (%s)") % store.name)
            order['data'].update({'to_invoice': True, 'real_to_invoice': False, 'partner_id': partner_id})
        else:
            order['data']['real_to_invoice'] = True
        result = super(InheritPosOrder, self)._process_order(order, draft, existing_order)
        self.browse(result).create_promotion_account_move()
        return result

    def action_view_invoice(self):
        action = super(InheritPosOrder, self).action_view_invoice()
        action.update({
            'view_mode': 'tree,form,kanban',
            'view_id': False,
            'view_ids': [
                (self.env.ref('account.view_account_move_kanban').id, 'kanban'),
                (self.env.ref('account.view_out_invoice_tree').id, 'tree'),
                (self.env.ref('account.view_move_form').id, 'form')
            ],
            'domain': [('id', 'in', self.invoice_ids.ids)]
        })
        return action


class InheritPosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_state_registration = fields.Boolean(string='Is State Registration')
    product_src_id = fields.Many2one(comodel_name='pos.order.line', string='Source Product')
    product_discount_ids = fields.One2many(comodel_name='pos.order.line', inverse_name='product_src_id', string='Discount Product')

    @api.onchange('product_id')
    def _onchange_is_state_registration(self):
        is_state_registration = False
        if self.product_id:
            point_promotion = self.env['points.promotion'].sudo().search(
                [('product_discount_id', '=', self.product_id.id)], limit=1
            )
            if point_promotion:
                is_state_registration = point_promotion.check_validity_state_registration()
        self.is_state_registration = is_state_registration

    @api.model_create_multi
    def create(self, values):
        pols = super(InheritPosOrderLine, self).create(values)
        order_id, source_id = 0, 0
        for pol in pols:
            if not pol.product_id.is_promotion:
                order_id, source_id = pol.order_id.id, pol.id
                continue
            if order_id and source_id and pol.product_src_id.id != source_id:
                pol.write({'product_src_id': source_id, 'discount': 0, 'tax_ids_after_fiscal_position': None})
        return pols
