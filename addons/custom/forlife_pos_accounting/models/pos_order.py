from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class InheritPosOrder(models.Model):
    _inherit = 'pos.order'

    real_to_invoice = fields.Boolean(string='Real To Invoice')

    @api.model
    def _order_fields(self, ui_order):
        results = super(InheritPosOrder, self)._order_fields(ui_order)
        results['real_to_invoice'] = ui_order['real_to_invoice']
        for line in ui_order['lines']:
            if line[-1]['product_id']:
                point_promotion = self.env['points.promotion'].sudo().search(
                    [('product_discount_id', '=', line[-1]['product_id'])], limit=1
                )
                line[-1]['is_state_registration'] = point_promotion and point_promotion.check_validity_state_registration()
        return results

    def _prepare_invoice_line(self, order_line):
        if order_line.product_id.check_is_promotion():
            return None
        invoice_line = super(InheritPosOrder, self)._prepare_invoice_line(order_line)
        invoice_line.update({
            'pos_order_line_id': order_line.id,
            'account_analytic_id': self.session_id.config_id.store_id.account_analytic_id.id,
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
        return super(InheritPosOrder, self)._process_order(order, draft, existing_order)


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
