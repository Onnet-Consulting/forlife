# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
import ast
from datetime import datetime, timedelta


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
            list_product_point = []
            product_point = self.lines.filtered(lambda x: x.discount_details_lines.type == 'point').mapped(
                'product_id.id')
            for line in self.lines:
                if line.is_promotion:
                    continue
                discount = 0
                amount_discount = sum(line.discount_details_lines.mapped('money_reduced'))
                if item.brand_id.code == 'FMT':
                    if line.qty > 0 and line.original_price > 0:
                        discount = round(((amount_discount / line.qty) / line.original_price) * 100)
                    if discount > 50:
                        discount = '50%+'
                    else:
                        discount = f'{discount}%'

                if item.brand_id.code == 'TKL':
                    discount = amount_discount
                    if amount_discount > 0:
                        discount = -1 * discount
                    else:
                        discount = discount
                if line.product_id.id not in product_point:
                    line_products.append({
                        'promotion_list': line.promotion_usage_ids.filtered(lambda x:x.program_id.promotion_type != 'pricelist').mapped('program_id.name'),
                        'name': line.product_id.name,
                        'qty': line.qty,
                        'barcode': line.product_id.barcode,
                        'price_unit': self.currency_id.custom_format(line.original_price, no_symbol=True),
                        'discount': discount,
                        'subtotal_paid': line.subtotal_paid,
                    })
                for p in line.promotion_usage_ids:
                    if not p.code_id:
                        continue
                    if p.program_id.promotion_type != 'code':
                        gif_code.append({'code': p.code_id.name, 'amount': 0})
                    else:
                        gif_code.append({
                            'code': p.code_id.name,
                            'amount': p.discount_total
                        })

                for promotion_detail in line.discount_details_lines:
                    if promotion_detail.type == 'point':
                        list_product_point.append({
                            'name': line.product_id.name,
                            'qty': line.qty,
                            'barcode': line.product_id.barcode,
                            'price_unit': self.currency_id.custom_format(line.original_price, no_symbol=True),
                            'discount': discount,
                            'subtotal_paid': line.subtotal_paid,
                        })
                        accumulation += promotion_detail.money_reduced

                amount_total += line.subtotal_paid
                total_qty += line.qty
                total_reduced += line.money_is_reduced
            payment_method = []
            for pm in item.payment_ids:
                payment_method.append({
                    'name': pm.payment_method_id.name,
                    'amount': f"{self.currency_id.custom_format(pm.amount)}",
                })
            store = 'forlife' if item.brand_id.code == 'TKL' else 'format'
            history_point = self.env['partner.history.point'].search([
                ('partner_id', '=', item.partner_id.id),
                ('date_order', '<=', item.date_order),
                ('store', '=', store)
            ])
            data.append({
                'brand': item.brand_id.code,
                'receipt_footer': item.brand_id.pos_receipt_footer,
                'address': '%s-%s-%s' % (
                    item.store_id.contact_id.street, item.store_id.contact_id.street2, item.store_id.contact_id.city),
                'phone': item.store_id.contact_id.phone,
                'qr_code': '',
                'date_order': (item.date_order + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S') if item.date_order else '',
                'order_name': item.pos_reference,
                'partner': item.partner_id.name,
                'employee': item.user_id.name,
                'note': '',
                'total_qty': total_qty,
                'total_reduced': self.currency_id.custom_format(total_reduced),
                'amount_total': self.currency_id.custom_format(amount_total),
                'line_products': self.sum_product_with_promotion(line_products),
                'list_product_point': list_product_point,
                'gif_code': self.sum_amount_code(gif_code),
                'amount_paid': self.currency_id.custom_format(item.amount_paid),
                'payment_method': payment_method,
                'accumulation': self.currency_id.custom_format(accumulation) if accumulation > 0 else 0,
                'total_point': item.total_point,
                'sum_total_point': sum(history_point.mapped('points_store')) if history_point else 0
            })
        if not item.partner_id.retail_type_ids.filtered(lambda x: x.retail_type == 'app'):
            data['qr_code'] = 'https://tokyolife.vn'
        return data

    def covert_to_list(self, data):
        return ast.literal_eval(data)

    def sum_amount_code(self, data):
        grouped_data = {}
        for item in data:
            code = item['code']
            if code in grouped_data:
                grouped_data[code] += item['amount']
            else:
                grouped_data[code] = item['amount']

        for d, value in grouped_data.items():
            value = self.currency_id.custom_format(value)
            grouped_data[d] = f'({value})'

        return grouped_data

    def sum_product_with_promotion(self, data):
        grouped_data = {}
        for item in data:
            code = f"{item['promotion_list']}"
            if code in grouped_data:
                grouped_data[code].append(item)
            else:
                grouped_data[code] = [item]

        for k, value in grouped_data.items():
            grouped_product = {}
            list_grouped_product = []
            for v in value:
                barcode = v['barcode']
                if barcode in grouped_product:
                    qty = grouped_product[barcode].get('qty', 0)
                    try:
                        discount = float(grouped_product[barcode].get('discount', 0))
                        subtotal_paid = float(grouped_product[barcode].get('subtotal_paid', 0))
                        v_discount = float(v['discount'])
                        v_subtotal_paid = float(v['subtotal_paid'])
                        total_discount = discount + v_discount
                        total_subtotal_paid = subtotal_paid + v_subtotal_paid
                    except:
                        total_discount = grouped_product[barcode].get('discount', 0)
                        total_subtotal_paid = grouped_product[barcode].get('subtotal_paid', 0)

                    grouped_product[barcode] = {
                        'promotion_list': v['promotion_list'],
                        'name': v['name'],
                        'barcode': v['barcode'],
                        'price_unit': v['price_unit'],
                        'qty': qty + v['qty'],
                        'discount': total_discount,
                        'subtotal_paid': total_subtotal_paid,
                    }
                else:
                    discount = v['discount']
                    subtotal_paid = v['subtotal_paid']
                    grouped_product[barcode] = {
                        'promotion_list': v['promotion_list'],
                        'name': v['name'],
                        'barcode': v['barcode'],
                        'price_unit': v['price_unit'],
                        'qty': v['qty'],
                        'discount': discount,
                        'subtotal_paid': subtotal_paid,
                    }

            for gp_k, gp_v in grouped_product.items():
                try:
                    gp_v['discount'] = self.currency_id.custom_format(gp_v['discount'], no_symbol=True)
                except:
                    pass
                try:
                    gp_v['subtotal_paid'] = self.currency_id.custom_format(gp_v['subtotal_paid'])
                except:
                    pass

                list_grouped_product.append(gp_v)
            grouped_data[k] = list_grouped_product
        return grouped_data

    @api.model
    def create_from_ui(self, orders, draft=False):
        try:
            order_ids = super().create_from_ui(orders, draft)
            for o in order_ids:
                order = self.sudo().browse(o['id'])
                store = 'forlife' if order.brand_id.code == 'TKL' else 'format'
                history_point = self.env['partner.history.point'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('date_order', '<=', order.date_order),
                    ('store', '=', store)
                ])
                o.update({
                    'total_point': order.total_point,
                    'sum_total_point': sum(history_point.mapped('points_store')) if history_point else 0,
                })
            return order_ids
        except:
            return super().create_from_ui(orders, draft)
