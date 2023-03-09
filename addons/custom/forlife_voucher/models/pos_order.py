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
            if quantity == 0:
                continue
            # xác định line tương ứng để cập nhật lại giá voucher bằng mệnh giá
            for item in res:
                if item[2] and item[2].get('product_id', False) and item[2].get('product_id', False) == line.product_id.id:
                    item[2]['price_unit'] = line.product_id.price
            res.append((0, None, {
                'account_id': line.product_id.categ_id.property_price_account_id.id,
                'quantity': quantity,
                'price_unit': -(line.product_id.price - line.price_unit),
                'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)],
            }))
        return res

    def action_create_voucher(self):
        for line in self.lines:
            program_voucher_id = line.product_id.program_voucher_id
            if not line.product_id.voucher or line.product_id.detailed_type != 'service' or not program_voucher_id or program_voucher_id.type != 'e' or line.qty <= line.x_qty_voucher:
                continue
            self.env['voucher.voucher'].create([{
                'program_voucher_id': program_voucher_id.id,
                'type': 'e',
                'brand_id': program_voucher_id.brand_id.id if program_voucher_id.brand_id else None,
                'store_ids': [(6, False, program_voucher_id.store_ids.ids)],
                'start_date': line.order_id.date_order,
                'state': 'sold',
                'price': line.product_id.price,
                'price_used': 0,
                'price_residual': line.product_id.price - 0,
                'derpartment_id': program_voucher_id.derpartment_id.id if program_voucher_id.derpartment_id else None,
                'end_date': program_voucher_id.end_date,
                'apply_many_times': program_voucher_id.apply_many_times,
                'apply_contemp_time': program_voucher_id.apply_contemp_time,
                'product_voucher_id': program_voucher_id.product_id.id if program_voucher_id.product_id else None,
                'purpose_id': program_voucher_id.purpose_id.id if program_voucher_id.purpose_id else None,
                'order_pos': line.order_id.id
            }] * int(line.qty - line.x_qty_voucher))
            line.x_qty_voucher = line.product_uom_qty
