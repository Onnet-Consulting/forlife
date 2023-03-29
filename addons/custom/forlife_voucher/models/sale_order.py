from odoo import api, fields, models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_view_voucher(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_voucher.forlife_voucher_action')
        action['domain'] = [('sale_id', '=', self.id)]
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped, final, date)
        for order in self:
            invoice_line_vals = []
            for line in order.order_line:
                if not line.product_id.categ_id.property_price_account_id or line.product_id.price - line.price_unit <= 0:
                    continue
                if line.product_id.program_voucher_id.type == 'v':
                    imei = []
                    move_line_ids = self.env['stock.move.line'].search([('move_id.sale_line_id', '=', line.id)])
                    for move_line_id in move_line_ids:
                        imei.append(move_line_id.lot_id.name)
                    quantity = self.env['voucher.voucher'].search_count(
                        [('sale_id', '=', self.id), ('purpose_id.purpose_voucher', '=', 'pay'), ('name', 'in', imei)])
                elif line.product_id.program_voucher_id.type == 'e' and line.product_id.program_voucher_id.purpose_id.purpose_voucher == 'pay':
                    quantity = line.qty_invoiced
                else:
                    quantity = 0
                if not quantity:
                    continue
                # xác định line tương ứng để cập nhật lại giá voucher bằng mệnh giá
                account_move_line_id = res.invoice_line_ids.filtered(
                    lambda x: x.product_id == line.product_id and x.price_unit != line.product_id.price)
                account_move_line_id.price_unit = line.product_id.price
                invoice_line_vals.append((0, 0, {
                    # 'display_type': line.display_type or 'line_section',
                    'sequence': line.sequence,
                    'account_id': line.product_id.categ_id.property_price_account_id.id,
                    'quantity': quantity,
                    # 'sale_line_ids': [Command.link(line.id)],
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                    'price_unit': -(line.product_id.price - line.price_unit),
                    'is_downpayment': line.is_downpayment,
                }))
            if invoice_line_vals:
                res.invoice_line_ids = invoice_line_vals
        return res


    def action_create_voucher(self):
        for line in self.order_line:
            program_voucher_id = line.product_id.program_voucher_id
            if not line.product_id.voucher or line.product_id.detailed_type != 'service' or not program_voucher_id or program_voucher_id.type != 'e' or line.product_uom_qty <= line.x_qty_voucher:
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
                'sale_id': line.order_id.id,
                'product_apply_ids':[(6, False, program_voucher_id.product_apply_ids.ids)],
                'is_full_price_applies': program_voucher_id.is_full_price_applies
            }] * int(line.product_uom_qty - line.x_qty_voucher))
            line.x_qty_voucher = line.product_uom_qty
