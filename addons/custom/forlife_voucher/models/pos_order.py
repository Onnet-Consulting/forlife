from unittest.case import _id

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_view_voucher(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_voucher.forlife_voucher_action')
        action['domain'] = [('order_pos', '=', self.id)]
        return action

    def _create_order_picking(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})
        res = super(PosOrder, self.with_context(ctx))._create_order_picking()
        return res

    def _prepare_invoice_lines(self):
        res = super(PosOrder, self)._prepare_invoice_lines()
        for line in self.lines:
            if not line.pack_lot_ids or not line.product_id.categ_id.property_price_account_id or line.product_id.price - line.price_unit <= 0:
                continue
            imei = line.pack_lot_ids.mapped('lot_name')
            quantity = self.env['voucher.voucher'].search_count(
                [('order_pos', '=', self.id), ('purpose_id.ref', '=ilike', 'B'), ('name', 'in', imei)])
            res.append((0, None, {
                'account_id': line.product_id.categ_id.property_price_account_id.id,
                'quantity': quantity,
                'price_unit': line.product_id.price - line.price_unit,
                'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)],
            }))
        return res
