import pytz
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

PROMOTION_JOURNAL_FIELD = {
    'points.promotion': 'account_journal_id',
    'promotion.program': 'journal_id',
    'member.card': 'journal_id'
}

# REWARD_TYPE = (
#     'combo_amount',
#     'combo_percent',
#     'combo_fixed_price',
#     'combo_percent_by_qty',
#     'combo_fixed_price_by_qty',
#     'code_amount',
#     'code_percent',
#     'code_fixed_price',
#     'cart_discount_percent',
#     'cart_discount_fixed_price'
# )


class InheritPosOrder(models.Model):
    _inherit = 'pos.order'

    real_to_invoice = fields.Boolean(string='Real To Invoice')
    invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='pos_order_id', string='Invoices')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @staticmethod
    def _create_promotion_account_move(order_line, partner_id, credit_account_id):
        display_name = order_line.product_id.get_product_multiline_description_sale()
        name = order_line.product_id.default_code + " " + display_name if order_line.product_id.default_code else display_name
        if order_line.refunded_orderline_id:
            credit_account_id = order_line.product_id.product_tmpl_id.categ_id.x_property_account_return_id.id
        elif not credit_account_id:
            # if order_line.is_reward_line:
            #     credit_account_id = order_line.product_id.product_tmpl_id.categ_id.product_gift_account_id.id
            # else:
            credit_account = order_line.product_id.product_tmpl_id._get_product_accounts()
            credit_account_id = (credit_account['income'] or credit_account['expense']).id

        return [
            (0, 0, {
                'partner_id': partner_id,
                'analytic_account_id': order_line.order_id.session_id.config_id.store_id.analytic_account_id.id or None,
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
                'account_id': credit_account_id or None,
                'credit': 0,
                'debit': order_line.price_unit if order_line.price_unit >= 0 else -order_line.price_unit,
            }), (0, 0, {
                'partner_id': partner_id,
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
                'credit': order_line.price_unit if order_line.price_unit >= 0 else -order_line.price_unit,
                'debit': 0,
            })
        ]

    def create_promotion_account_move(self):
        self.ensure_one()
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        invoice_date = fields.Datetime.now() if self.session_id.state == 'closed' else self.date_order
        values = {}
        results = self.env['account.move']
        for line in self.lines:
            if not line.product_src_id:
                continue
            promotion = self.env[line.promotion_model].sudo().browse(line.promotion_id)
            # if line.promotion_model == 'promotion.program' and promotion.reward_type not in REWARD_TYPE:
            #     continue
            journal = promotion[PROMOTION_JOURNAL_FIELD[line.promotion_model]]
            if not journal:
                raise ValidationError(_("Cannot found journal promotion's product %s") % line.product_id.name)
            partner_id = journal.company_consignment_id.id or self.partner_id.id
            credit_account_id = journal.default_account_id.id
            _key = ','.join((line.promotion_model, str(line.promotion_id)))
            if _key in values:
                values[_key]['line_ids'] += self._create_promotion_account_move(line, partner_id, credit_account_id)
            else:
                values[_key] = {
                    'invoice_origin': self.name,
                    'journal_id': journal.id,
                    'pos_order_id': self.id,
                    'move_type': 'entry',
                    'ref': self.name,
                    'partner_id': self.partner_id.id,
                    'partner_bank_id': self._get_partner_bank_id(),
                    # considering partner's sale pricelist's currency
                    'currency_id': self.pricelist_id.currency_id.id,
                    'invoice_user_id': self.user_id.id,
                    'invoice_date': invoice_date.astimezone(timezone).date(),
                    'fiscal_position_id': self.fiscal_position_id.id,
                    'line_ids': self._create_promotion_account_move(line, partner_id, credit_account_id),
                    'invoice_payment_term_id': self.partner_id.property_payment_term_id.id or False,
                    'invoice_cash_rounding_id': self.config_id.rounding_method.id
                    if self.config_id.cash_rounding and (not self.config_id.only_round_cash_method or any(
                        p.payment_method_id.is_cash_count for p in self.payment_ids))
                    else False,
                    'narration': self.note or None
                }

        if values:
            results = results.create([values[k] for k in values])
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
        if order_line.product_src_id:
            return None
        invoice_line = super(InheritPosOrder, self)._prepare_invoice_line(order_line)
        invoice_line.update({
            'pos_order_line_id': order_line.id,
            'account_analytic_id': self.session_id.config_id.store_id.analytic_account_id.id,
            'partner_id': order_line.order_id.partner_id.id,
            'price_unit': order_line.original_price if not order_line.is_reward_line else 0
        })
        if order_line.refunded_orderline_id:
            invoice_line.update({
                'account_id': order_line.product_id.product_tmpl_id.categ_id.x_property_account_return_id.id
            })
            if not invoice_line['account_id']:
                raise ValidationError(_(
                    'Product categories "%s" has not configured refund account!',
                    order_line.product_id.product_tmpl_id.categ_id.display_name
                ))
            return invoice_line
        journal = self.session_id.config_id.invoice_journal_id
        if journal.company_consignment_id:
            invoice_line.update({
                'partner_id': journal.company_consignment_id.id,
                'account_id': journal.default_account_id.id
            })
        return invoice_line

    def _prepare_invoice_lines(self):
        return [
            invoice_line
            for invoice_line in super(InheritPosOrder, self)._prepare_invoice_lines()
            if invoice_line[-1] is not None
        ]

    def _prepare_invoice_vals(self):
        result = super(InheritPosOrder, self)._prepare_invoice_vals()
        if self.to_invoice and self.real_to_invoice:
            result.update({'exists_bkav': True, 'is_post_bkav': True})
        if not self.real_to_invoice:
            partner_id = self.session_id.config_id.store_id.contact_id.id
            if not partner_id:
                raise ValidationError(_("Cannot found contact's store (%s)") % self.pos_session_id.config_id.store_id.name)
            result['partner_id'] = partner_id
        result['pos_order_id'] = self.id
        return result

    @api.model
    def _process_order(self, order, draft, existing_order):
        pol_object = self.env['pos.order.line']
        to_invoice = order['data']['to_invoice']
        order['data'].update(not to_invoice and {'to_invoice': True, 'real_to_invoice': False} or {'real_to_invoice': False})
        currency_id = self.env['product.pricelist'].browse(order['data']['pricelist_id']).currency_id
        for line in order['data']['lines']:
            if 'refunded_orderline_id' in line[-1] and line[-1]['refunded_orderline_id']:
                line[-1].update(pol_object.browse(line[-1]['refunded_orderline_id']).generate_promotion_values(line[-1]['qty']))

            price = 0 if line[-1]['is_reward_line'] else line[-1]['original_price'] * (1 - (line[-1]['discount'] or 0.0) / 100.0)
            taxes = self.env['account.tax'].browse(line[-1]['tax_ids'][0][-1])
            if not taxes:
                price_subtotal = price * line[-1]['qty']
                line[-1].update({'price_subtotal': price_subtotal, 'price_subtotal_incl': price_subtotal})
            else:
                tax = taxes.compute_all(price, currency_id, line[-1]['qty'], product=self.env['product.product'].browse(line[-1]['product_id']), partner=False)
                line[-1].update({'price_subtotal': tax['total_excluded'], 'price_subtotal_incl': tax['total_included']})
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
    promotion_model = fields.Char(string='Promotion Model')
    promotion_id = fields.Many2oneReference(string='Promotion ID', model_field='promotion_model')
    is_promotion = fields.Boolean(string='Is promotion')
    subtotal_paid = fields.Monetary(compute='_compute_subtotal_paid')

    def _compute_subtotal_paid(self):
        for pol in self:
            pol.subtotal_paid = 0 if pol.is_reward_line else pol.price_subtotal_incl - pol.money_is_reduced

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

    def _prepare_pol_promotion_line(self, product_id, price, promotion, is_state_registration=False):
        if promotion._name == 'promotion.program' and not product_id:
            raise ValidationError(_('No product that represent the promotion %s!', promotion.name))
        return {
            'order_id': self.order_id.id,
            'product_src_id': self.id,
            'promotion_id': promotion.id,
            'promotion_model': promotion._name,
            'qty': 1 if not self.refunded_orderline_id else -1,
            'price_unit': price,
            'price_subtotal': price,
            'price_subtotal_incl': price,
            'discount': 0,
            'product_id': product_id.id,
            'tax_ids': [[6, False, product_id.taxes_id.ids]],
            'pack_lot_ids': [],
            'full_product_name': product_id.name,
            'price_extra': 0,
            'point': None,
            'is_new_line_point': False,
            'original_price': price,
            'card_rank_discount': 0,
            'card_rank_applied': False,
            'employee_id': self.employee_id.id,
            'expire_change_refund_date': '',
            'quantity_canbe_refund': 0,
            'reason_refund_id': 0,
            'money_is_reduced': 0,
            'money_point_is_reduced': 0,
            'is_product_defective': False,
            'money_reduce_from_product_defective': 0,
            'product_defective_id': 0,
            'is_state_registration': is_state_registration,
            'name': product_id.name,
            'is_promotion': True
        }

    def prepare_pol_promotion_lines(self):
        if any(not promotion.program_id.product_discount_id for promotion in self.promotion_usage_ids):
            raise ValidationError(_('Please configure before apply promotion program to POS order!'))
        pol = self.refunded_orderline_id or self
        if any(
            (discount.type == 'card' and not pol.order_id.card_rank_program_id.product_discount_id)
            or (discount.type == 'point' and not pol.order_id.program_store_point_id.product_discount_id)
            for discount in self.discount_details_lines if discount.type in ('card', 'point')
        ):
            raise ValidationError(_('Please configure before apply card/point to POS order!'))
        return [
            self._prepare_pol_promotion_line(
                product_id=promotion.program_id.product_discount_id,
                price=-promotion.discount_total,
                promotion=promotion.program_id,
            ) for promotion in self.promotion_usage_ids
        ] + [
            self._prepare_pol_promotion_line(
                product_id=pol.order_id.card_rank_program_id.product_discount_id if discount.type == 'card' else pol.order_id.program_store_point_id.product_discount_id,
                price=-discount.money_reduced,
                promotion=pol.order_id.card_rank_program_id if discount.type == 'card' else pol.order_id.program_store_point_id,
                is_state_registration=False if discount.type == 'card' else pol.order_id.program_store_point_id.check_validity_state_registration(),
            ) for discount in self.discount_details_lines if discount.type in ('card', 'point')
        ]

    @api.model_create_multi
    def create(self, values):
        pols = super(InheritPosOrderLine, self).create(values)
        pols_promotion_values = []
        for pol in pols:
            if pol.is_reward_line:
                continue
            pols_promotion_values += pol.prepare_pol_promotion_lines()
        if pols_promotion_values:
            self.create(pols_promotion_values)
        return pols

    def generate_promotion_values(self, original_qty=0):
        return {
            'is_reward_line': self.is_reward_line,
            'promotion_usage_ids': [(0, 0, {
                'program_id': p.program_id.id,
                'currency_id': p.currency_id.id,
                'discount_amount': p.discount_amount,
                'code_id': p.code_id.id,
                'pro_priceitem_id': p.pro_priceitem_id.id,
                'str_id': p.str_id,
                'original_price': p.original_price,
                'new_price': p.new_price,
                'discount_based_on': p.discount_based_on,
                'promotion_type': p.promotion_type,
                'registering_tax': p.registering_tax,
                'display_name': p.display_name
            }) for p in self.promotion_usage_ids],
            'discount_details_lines': [(0, 0, {
                'type': p.type,
                'program_name': p.program_name.id,
                'listed_price': -p.listed_price,
                'recipe': p.recipe / self.qty * original_qty,
                'discounted_amount': p.discounted_amount / self.qty * original_qty
            }) for p in self.discount_details_lines],
        }


