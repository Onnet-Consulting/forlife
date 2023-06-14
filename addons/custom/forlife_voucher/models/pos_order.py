from unittest.case import _id

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    pos_voucher_line_ids = fields.One2many('pos.voucher.line','pos_order_id', string='Vouchers')

    @api.model
    def _process_order(self, order, draft, existing_order):
        pos_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        if not existing_order:
            pos = self.env['pos.order'].browse(pos_id)
            if len(pos.pos_voucher_line_ids) > 0:
                for v in pos.pos_voucher_line_ids:
                    v.voucher_id.price_used = v.voucher_id.price_used + v.price_used
                    v.voucher_id._compute_price_residual()
                    if v.voucher_id.apply_many_times:
                        if v.voucher_id.price_residual > 0:
                            v.voucher_id.state = 'valid'
                        if v.voucher_id.price_residual == 0:
                            v.voucher_id.state = 'off value'
                    else:
                        if v.voucher_id.price_residual == 0:
                            v.voucher_id.state = 'off value'
                        if v.voucher_id.price_residual > 0:
                            pos.generate_account_journal(voucher=v)
                            v.voucher_id.state = 'off value'
                            v.voucher_id.price_residual = 0
                    v.voucher_id.order_use_ids = [(4, pos.id)]
            pos.action_create_voucher()
        return pos_id

    def generate_account_journal(self, voucher):
        move_vals = {
            'ref': self.name,
            'date': self.date_order,
            'journal_id': voucher.payment_method_id.journal_id.id,
            'company_id': self.company_id.id,
            'move_type': 'entry',
            'pos_order_id': self.id,
            'line_ids': [
                (0, 0, {
                    'name': 'Write off giá trị còn lại của Voucher sử dụng 1 lần mã {}'.format(voucher.voucher_id.name),
                    'account_id': voucher.payment_method_id.account_other_income.id,
                    'debit': 0.0,
                    'credit': voucher.voucher_id.price_residual,
                    'analytic_distribution': {
                        voucher.voucher_id.derpartment_id.center_expense_id.id: 100} if voucher.voucher_id.derpartment_id.center_expense_id else {}
                }),
                # credit line
                (0, 0, {
                    'name': 'Write off giá trị còn lại của Voucher sử dụng 1 lần mã {}'.format(voucher.voucher_id.name),
                    'account_id': voucher.payment_method_id.account_general.id,
                    'debit': voucher.voucher_id.price_residual,
                    'credit': 0.0,
                    'analytic_distribution': {
                        voucher.voucher_id.derpartment_id.center_expense_id.id: 100} if voucher.voucher_id.derpartment_id.center_expense_id else {}
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)._post()
        return True


    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['pos_voucher_line_ids'] = [v for v in ui_order['voucherlines']] if ui_order['voucherlines'] else False
        return res

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
            if not line.product_id.categ_id.property_price_account_id or line.product_id.price - line.price_unit <= 0:
                continue
            if line.product_id.program_voucher_id.type == 'v':
                imei = line.pack_lot_ids.mapped('lot_name')
                quantity = self.env['voucher.voucher'].search_count(
                    [('order_pos', '=', self.id), ('purpose_id.purpose_voucher', '=', 'pay'), ('name', 'in', imei)])
            elif line.product_id.program_voucher_id.type == 'e' and line.product_id.program_voucher_id.purpose_id.purpose_voucher == 'pay':
                quantity = line.qty
            else:
                quantity = 0
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
                'partner_id': line.order_id.partner_id.id if line.order_id.partner_id else None,
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
            line.x_qty_voucher = line.qty

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'voucherlines': [voucher for voucher in order.pos_voucher_line_ids.export_for_ui()],
        })
        return result
