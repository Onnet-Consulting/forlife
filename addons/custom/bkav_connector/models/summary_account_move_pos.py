# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class SummaryAccountMovePos(models.Model):
    _name = 'summary.account.move.pos'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    partner_id = fields.Many2one('res.partner')
    store_id = fields.Many2one('store')
    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã phát hành')], string="State", default='draft')
    line_ids = fields.One2many('summary.account.move.pos.line', 'summary_id')
    company_id = fields.Many2one('res.company')
    number_bill = fields.Char('Số hóa đơn')
    einvoice_status = fields.Selection([('draft', 'Draft')], string=' Trạng thái HDDT')
    einvoice_date = fields.Date(string="Ngày phát hành")

    def collect_invoice_return_end_day(self):
        moves = self.env['account.move']
        today = date.today() - timedelta(days=1)
        invoice_pos = moves.search([('company_id', '=', self.env.company.id),
                                 ('is_post_bkav', '=', False),
                                 ('pos_order_id', '!=', False),
                                 ('move_type', 'in', ('out_refund', 'out_invoice')),
                                 ('invoice_date', '<=', today)])
        invoice_pos_return = invoice_pos.filtered(lambda x: x.pos_order_id.refunded_order_ids)
        data_store = {}
        stores = invoice_pos_return.mapped('pos_order_id.store_id')
        for store in stores:
            data_store.update({
                store.id: {
                    'products': {}
                }
            })

        for move in invoice_pos_return:
            pos_order_id = move.pos_order_id
            store_id = pos_order_id.store_id
            products = data_store.get(store_id.id).get('products')
            for line in pos_order_id.lines:
                if not line.product_id.barcode:
                    continue
                item = (line.product_id.barcode, line.price_bkav)
                if not products.get(item):
                    products.update({
                        item: {
                            'product_id': line.product_id.id,
                            'quantity': line.qty,
                            'price_unit': line.price_bkav,
                            'pos_order_ids': [line.order_id.id]
                        }
                    })
                else:
                    products[item]['quantity'] += line.qty
                    products[item]['pos_order_ids'] += [line.order_id.id]

        record_ids = []
        for store in stores:
            products = data_store.get(store.id).get('products')
            lines = []
            for item in products:
                lines.append((0, 0, {
                    'product_id': products.get(item).get('product_id'),
                    'quantity': products.get(item).get('quantity'),
                    'price_unit': products.get(item).get('price_unit'),
                    'invoice_ids': [(6, 0, products.get(item).get('pos_order_ids'))]
                }))
            vals = {
                'company_id': self.env.company.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': lines
            }
            record = self.env['summary.account.move.pos.return'].create(vals)
            record_ids.append(record.id)
        return record_ids

    def collect_invoice_sale_end_day(self):
        moves = self.env['account.move']
        sale_ids = []
        today = date.today() - timedelta(days=1) # Do job chạy 2h sáng nên gom đơn ngày hqua phải - 1
        invoices = moves.search([('company_id', '=', self.env.company.id),
                                 ('move_type', '=', 'out_invoice'),
                                 ('is_post_bkav', '=', False),
                                 ('pos_order_id', '!=', False),
                                 ('invoice_date', '<=', today)])
        invoices = invoices.filtered(lambda x: not x.pos_order_id.refunded_order_ids)
        stores = invoices.mapped('pos_order_id.store_id')
        for store in stores:
            move_line = []
            move_line_vals = []
            for inv in invoices:
                if inv.pos_order_id.store_id.id == store.id:
                    move_line.extend(inv.pos_order_id.lines.ids)
            for line in move_line:
                invoice_ids = []
                line_id = self.env['pos.order.line'].browse(line)
                qty = line_id.qty
                invoice_ids.append(line_id.order_id.id)
                for line2 in move_line:
                    line2_id = self.env['pos.order.line'].browse(line2)
                    if line_id.product_id.barcode == line2_id.product_id.barcode \
                            and line_id.price_bkav == line2_id.price_bkav and line_id.id != line2_id.id:
                        qty += line2_id.qty
                        invoice_ids.append(line2_id.order_id.id)
                        move_line.remove(line2)
                move_line_vals.append((0, 0, {
                    'product_id': line_id.product_id.id,
                    'quantity': qty,
                    'price_unit': line_id.price_bkav,
                    'invoice_ids': [(6, 0, invoice_ids)]
                }))
            sale = self.env['summary.account.move.pos'].create({
                'company_id': self.env.company.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': move_line_vals
            })
            sale_ids.append(sale.id)
        return sale_ids

    def collect_clearing_the_end_day(self):
        sale_ids = self.collect_invoice_sale_end_day()
        sales = self.env['summary.account.move.pos'].browse(sale_ids)
        refund_ids = self.collect_invoice_return_end_day()
        refunds = self.env['summary.account.move.pos.return'].browse(refund_ids)
        matching_records, different_records = self.find_matching_store_id(sales, refunds)
        data_match = self.get_value_synthetic_move_match(matching_records)
        data_diff = self.get_value_synthetic_move_diff(different_records)
        vals_posi = data_match[0] + data_diff[0]
        vals_neg = data_match[1] + data_diff[1]
        return vals_posi, vals_neg

    def find_summary(self, res):
        summary_return_line_id = self.env['summary.account.move.pos.return.line'].browse(res.get('return_line_id'))
        pos_order_return_ids = summary_return_line_id.invoice_ids
        pos_order_sale_ids = pos_order_return_ids.mapped('refunded_order_ids')
        pos_order_ids_sorted = pos_order_sale_ids.sorted('create_date')
        quantity = res.get('quantity')
        product_id = self.env['product.product'].browse(res.get('product_id'))
        price_unit = res.get('price_unit')
        synthetic_ids = []

        for i in range(len(pos_order_ids_sorted)):
            if quantity == 0:
                break
            pos_order = pos_order_ids_sorted[i]
            products = pos_order.lines.mapped('product_id')
            price_bkavs = pos_order.lines.mapped('price_bkav')
            lines = pos_order.lines.filtered(lambda x: x.product_id.id == product_id.id and
                                            x.price_bkav == price_unit)
            invoice_date_from = pos_order.create_date.replace(hour=0, minute=0, second=0)
            invoice_date_to = pos_order.create_date.replace(hour=23, minute=59, second=59)
            synthetic_id = self.env['synthetic.account.move.pos'].search([('invoice_date', '>=', invoice_date_from),
                                                                          ('invoice_date', '<=', invoice_date_to)],
                                                                         limit=1)

            for line in lines:
                if not line.product_id.barcode:
                    continue
                if quantity == 0:
                    break
                if quantity + line.qty < 0:
                    synthetic_ids.append({
                        'product_id': product_id,
                        'quantity': line.qty,
                        'price_unit': price_unit,
                        'synthetic_id': synthetic_id.id,
                        'pos_order': pos_order.id
                    })
                    quantity += line.qty
                else:
                    synthetic_ids.append({
                        'product_id': product_id,
                        'quantity': abs(quantity),
                        'price_unit': price_unit,
                        'synthetic_id': synthetic_id.id,
                        'pos_order': pos_order.id
                    })
                    quantity = 0
        return synthetic_ids

    def make_adjusted_invoice_pos(self, vals_neg):
        record_ids = []
        for data_store in vals_neg:
            source_invoices = {}
            summary_parents = []
            for line in data_store.get('line_ids'):
                summary_parents += self.find_summary(line[2])
            for item in summary_parents:
                if not source_invoices.get(item.get('synthetic_id')):
                    source_invoices.update({
                        item.get('synthetic_id'): [item]
                    })
                else:
                    source_invoices.update({
                        item.get('synthetic_id'): source_invoices.get(item.get('synthetic_id')) + [item]
                    })

            for invoice in source_invoices:
                products = {}
                for pos_order_line in source_invoices.get(invoice):
                    item = (pos_order_line.get('product_id').barcode, pos_order_line.get('price_unit'))
                    if not products.get(item):
                        products.update({
                            item: {
                                'product_id': pos_order_line.get('product_id').id,
                                'quantity': pos_order_line.get('quantity'),
                                'price_unit': pos_order_line.get('price_unit'),
                                'pos_order_ids': [pos_order_line.get('pos_order')]
                            }
                        })
                    else:
                        pos_order_ids = products.get(item).get('pos_order_ids')
                        quantity = products.get(item).get('quantity')
                        products.get(item).update({
                            'quantity': quantity + pos_order_line.get('quantity'),
                            'pos_order_ids': pos_order_ids + [pos_order_line.get('pos_order')]
                        })
                lines = []
                for item in products:
                    lines.append((0, 0, {
                        'product_id': products.get(item).get('product_id'),
                        'quantity': products.get(item).get('quantity'),
                        'price_unit': products.get(item).get('price_unit'),
                        'invoice_ids': [(6, 0, products.get(item).get('pos_order_ids'))]
                    }))

                store = self.env['store'].browse(data_store.get('store_id'))
                vals = {
                    'company_id': self.env.company.id,
                    'store_id': store.id,
                    'source_invoice': invoice,
                    'source_einvoice': invoice.number_bill if invoice else '',
                    'partner_id': store.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': lines
                }
                record = self.env['summary.adjusted.invoice.pos'].create(vals)
                record_ids.append(record.id)
        res = self.env['summary.adjusted.invoice.pos'].browse(record_ids)
        return res

    def get_val_synthetic_account(self):
        vals, vals_neg = self.collect_clearing_the_end_day()
        synthetic = self.env['synthetic.account.move.pos'].create(vals)
        adjusted_invoice = self.make_adjusted_invoice_pos(vals_neg)
        return synthetic, adjusted_invoice

    def find_matching_store_id(self, sales, refunds):
        matching_records = {}
        different_records = []
        merge = []
        for sale in sales:
            for refund in refunds:
                if sale.store_id == refund.store_id:
                    matching_records.update({
                        sale.store_id.id: [sale, refund]
                    })
                    merge.append(sale)
                    merge.append(refund)
        for sale in sales:
            if sale not in merge:
                different_records.append(sale)
        for refund in refunds:
            if refund not in merge:
                different_records.append(refund)
        return matching_records, different_records

    def get_value_synthetic_move_match(self, matching_records):
        vals_posi = []
        vals_neg = []
        for item in matching_records:
            store_id = self.env['store'].browse(int(item))
            sale_id = matching_records[item][0]
            refund_id = matching_records[item][1]
            dict_item = {}
            move_line_posi_val = []
            move_line_neg_val = []
            for sale in sale_id.line_ids:
                if not sale.barcode:
                    continue
                dict_item.update({
                    (sale.barcode, sale.price_unit): {
                        'product_id': sale.product_id.id,
                        'quantity': sale.quantity,
                        'price_unit': sale.price_unit,
                        'summary_line_id': sale.id,
                        'invoice_ids': [(6, 0, sale.invoice_ids.ids)]
                    }
                })
            for ref in refund_id.line_ids:
                if not ref.barcode:
                    continue
                if (ref.barcode, ref.price_unit) in dict_item:
                    dict_item[(ref.barcode, ref.price_unit)]['quantity'] += ref.quantity
                    invoice_ids = dict_item[(ref.barcode, ref.price_unit)]['invoice_ids'][0][2]
                    new_invoice_ids = invoice_ids + ref.invoice_ids.ids
                    dict_item[(ref.barcode, ref.price_unit)]['invoice_ids'] = [(6, 0, new_invoice_ids)]
                    dict_item[(ref.barcode, ref.price_unit)]['return_line_id'] = ref.id
                else:
                    dict_item.update({
                        (ref.barcode, ref.price_unit): {
                            'product_id': ref.product_id.id,
                            'quantity': ref.quantity,
                            'price_unit': ref.price_unit,
                            'return_line_id': ref.id,
                            'invoice_ids': [(6, 0, ref.invoice_ids.ids)]
                        }
                    })
            for line in dict_item:
                if dict_item.get(line).get('quantity') > 0:
                    move_line_posi_val.append((0, 0, dict_item.get(line)))
                elif dict_item.get(line).get('quantity') < 0:
                    move_line_neg_val.append((0, 0, dict_item.get(line)))
            if move_line_posi_val:
                vals_posi.append({
                    'company_id': self.env.company.id,
                    'store_id': store_id.id,
                    'partner_id': store_id.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': move_line_posi_val
                })
            if move_line_neg_val:
                vals_neg.append({
                    'company_id': self.env.company.id,
                    'store_id': store_id.id,
                    'partner_id': store_id.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': move_line_neg_val
                })
        return vals_posi, vals_neg

    def get_value_synthetic_move_diff(self, different_records):
        vals_posi = []
        vals_neg = []
        move_line_posi_val = []
        move_line_neg_val = []
        for item in different_records:
            for line in item.line_ids:
                lines = (0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit
                })
                if line.quantity > 0:
                    move_line_posi_val.append(lines)
                elif line.quantity < 0:
                    move_line_neg_val.append(lines)
            if move_line_posi_val:
                vals_posi.append({
                    'company_id': self.env.company.id,
                    'store_id': item.store_id.id,
                    'partner_id': item.store_id.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': move_line_posi_val
                })
            if move_line_neg_val:
                vals_neg.append({
                    'company_id': self.env.company.id,
                    'store_id': item.store_id.id,
                    'partner_id': item.store_id.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': move_line_neg_val
                })
        return vals_posi, vals_neg


class SummaryAccountMovePosLine(models.Model):
    _name = 'summary.account.move.pos.line'

    summary_id = fields.Many2one('summary.account.move.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế', related="product_id.taxes_id")
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="compute_price_subtotal")
    amount_total = fields.Monetary('Thành tiền', compute="compute_amount_total")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = r.price_unit * r.quantity - r.discount_amount

    @api.depends('price_subtotal', 'tax_amount')
    def compute_amount_total(self):
        for r in self:
            r.amount_total = r.price_subtotal + r.tax_amount

    @api.depends('tax_ids', 'price_subtotal')
    def compute_tax_amount(self):
        for r in self:
            if r.tax_ids:
                tax_amount = 0
                for tax in r.tax_ids:
                    tax_amount += (r.price_subtotal * tax.amount) / 100
                r.tax_amount = tax_amount
            else:
                r.tax_amount = 0
