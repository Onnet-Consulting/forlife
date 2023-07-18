# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import locale


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _order_fields(self, ui_order):
        data = super(PosOrder, self)._order_fields(ui_order)
        data['note'] = ui_order.get('note') or ''
        return data

    def print_pos_order(self):
        return self.env.ref('forlife_pos_print_receipt.print_print_order_pos_action').report_action(self)

    @api.model
    def prepare_data_receipt_report(self):
        data = []
        for item in self:
            total_qty = 0
            total_reduced = 0
            line_products = []
            gif_code = []
            amount_total = 0
            accumulation = 0
            for line in self.lines:
                discount = 0
                if item.brand_id.code == 'FMT':
                    if line.qty > 0 and line.original_price > 0:
                        discount = round(((line.money_is_reduced / line.qty) / line.original_price) * 100)
                    if discount > 50:
                        discount = f'{discount}%+'
                    else:
                        discount = f'{discount}%'

                if item.brand_id.code == 'TKL':
                    discount = self.env.company.currency_id.format(line.original_price)
                    if line.original_price > 0:
                        discount = f'-{discount}'
                    else:
                        discount = f'{discount}'

                line_products.append({
                    'promotion_list': line.promotion_usage_ids.mapped('program_id.name'),
                    'name': line.product_id.name,
                    'qty': line.qty,
                    'barcode': line.product_id.barcode,
                    'price_unit': self.env.company.currency_id.format(line.original_price),
                    'discount': discount,
                    'subtotal_paid': self.env.company.currency_id.format(line.subtotal_paid),
                })
                for p in line.promotion_usage_ids:
                    if not p.code_id:
                        continue
                    if p.program_id.promotion_type != 'code':
                        gif_code.append({'code': p.code_id.name, 'amount': 0})
                    else:
                        gif_code.append({'code': p.code_id.name,
                                         'amount': self.env.company.currency_id.format(p.discount_total)})

                for promotion_detail in line.discount_details_lines:
                    if promotion_detail.type != 'point':
                        continue
                    accumulation += promotion_detail.money_reduced

                amount_total += line.subtotal_paid
                total_qty += line.qty
                total_reduced += line.money_is_reduced
            payment_method = []
            for pm in item.payment_ids:
                payment_method.append({
                    'name': pm.payment_method_id.name,
                    'amount': f"({self.env.company.currency_id.format(pm.amount)})",
                })
            history_point = self.env['partner.history.point'].search([
                ('partner_id', '=', item.partner_id.id),
                ('date_order', '<=', item.date_order),
                ('store', '=', 'format')
            ])
            data.append({
                'brand': item.brand_id.code,
                'receipt_footer': item.brand_id.pos_receipt_footer,
                'address': '%s-%s-%s' % (
                    item.store_id.contact_id.street, item.store_id.contact_id.street2, item.store_id.contact_id.city),
                'phone': item.store_id.contact_id.phone,
                'qr_code': '',
                'date_order': item.date_order.strftime('%d/%m/%Y %H:%M:%S') if item.date_order else '',
                'order_name': item.pos_reference,
                'partner': item.partner_id.name,
                'employee': item.user_id.name,
                'note': '',
                'total_qty': total_qty,
                'total_reduced': self.env.company.currency_id.format(total_reduced),
                'amount_total': self.env.company.currency_id.format(amount_total),
                'line_products': line_products,
                'gif_code': gif_code,
                'amount_paid': self.env.company.currency_id.format(item.amount_paid),
                'payment_method': payment_method,
                'accumulation': accumulation,
                'total_point': item.total_point,
                'sum_total_point': sum(history_point.mapped('points_store')) if history_point else 0
            })
        return data
