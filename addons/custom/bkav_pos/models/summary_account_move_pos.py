# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from .utils import get_random_string

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

    # def create_mapping_product_by_store(self, invoices):
    #     data = {}
    #     stores = invoices.mapped('pos_order_id.store_id')
    #     for store in stores:
    #         data.update({
    #             store.id: {
    #                 'products': {}
    #             }
    #         })
    #     return data

    

    def create_move_line(self, line, lines_store={}, product_line_rel={}):
        product_id = line.product_id.id
        row = {line.id: line}

        if product_line_rel.get(product_id):
            old_row = product_line_rel[product_id]
            add_line = True
            for k, v in old_row.items():
                if v.price_bkav == line.price_bkav:
                    add_line = False
                    lines_store[k]["quantity"] += v.qty
                    invoice_ids = lines_store[k]["invoice_ids"]
                    invoice_ids.append(line.order_id.id)
                    lines_store[k]["invoice_ids"] = list(set(invoice_ids))
                    break
            if add_line:
                product_line_rel[product_id].update(row)
                lines_store[line.id] = {
                    "product_id": product_id,
                    "quantity": line.qty,
                    "price_unit": line.price_bkav,
                    "invoice_ids": [line.order_id.id]
                }
        else:
            product_line_rel[product_id] = row
            lines_store[line.id] = {
                "product_id": product_id,
                "quantity": line.qty,
                "price_unit": line.price_bkav,
                "invoice_ids": [line.order_id.id]
            }


    def compare_move_lines(
        self, 
        items={}, 
        store={}, 
        lines=[], 
        missing_line=[], 
        page=0, 
        first_n=0, 
        last_n=1000
    ):
        pk = f"{store.id}_{page}"
        lines_store = {}
        product_line_rel = {}
        if len(lines) > last_n:
            n = last_n - 1
            if x:= len(missing_line):
                n = n - x
            
            for line in missing_line:
                self.create_move_line(line, lines_store, product_line_rel)

            missing_line = []

            last_line = lines[n]
            pre_last_line = lines[n - 1]

            po_order_id = None
            if pre_last_line.order_id == last_line.order_id:
                po_order_id = last_line.order_id.id

            separate_lines = lines[first_n:last_n]
            del lines[first_n:last_n]

            for line in separate_lines:
                if po_order_id and line.order_id.id == po_order_id:
                    missing_line.append(line)
                    continue

                self.create_move_line(line, lines_store, product_line_rel)

            
            items[pk] = {
                'code': get_random_string(32),
                'company_id': self.env.company.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': list(lines_store.values())
            }
            page += 1
            self.compare_move_lines(items=items, store=store, lines=lines, missing_line=missing_line, page=page, first_n=first_n, last_n=last_n)
        else:
            for line in lines:
                self.create_move_line(line, lines_store, product_line_rel)
            items[pk] = {
                'code': get_random_string(32),
                'company_id': self.env.company.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': list(lines_store.values())
            }

        


    def collect_sales_invoice_to_bkav_end_day(self):
        invoice_model = self.env['account.move']
        today = date.today() - timedelta(days=1)
        domain = [
            ('company_id', '=', self.env.company.id),
            ('is_post_bkav', '=', False),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '<=', today),
            ('pos_order_id', '!=', False), 
        ]
        sale_invoices = invoice_model.search(domain)
        pos_order_ids = sale_invoices.mapped("pos_order_id")

        pos_order = self.env['pos.order'].search(
            [('id', 'in', pos_order_ids.ids)]
        ).filtered(lambda r: r.store_id.is_post_bkav == True)

        lines = self.env['pos.order.line'].search([
            ('order_id', 'in', pos_order.ids),
            ('qty', '>', 0)
        ])
        stores = pos_order.mapped("store_id")
        items = {}
        for store in stores:
            lines_store = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
            self.compare_move_lines(
                items=items,
                store=store,
                lines=list(lines_store),
                missing_line=[],
                page=0, 
                first_n=0, 
                last_n=200
            )
        # print(items)
        for k, v in items.items():
            res_line = self.env['summary.account.move.pos.line'].create(v["line_ids"])
            v["line_ids"] = res_line.ids

        vals_list = list(items.values())

        res = self.env['summary.account.move.pos'].create(vals_list)
        return res


    """
    def collect_invoice_return_end_day(self):
        moves = self.env['account.move']
        today = date.today() - timedelta(days=1)
        invoice_pos_return = moves.search([('company_id', '=', self.env.company.id),
                                 ('is_post_bkav', '=', False),
                                 ('pos_order_id', '!=', False),
                                 ('move_type', '=', 'out_refund'),
                                 ('invoice_date', '<=', today)])
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
                if line.qty >=0:
                    continue
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
        stores = invoices.mapped('pos_order_id.store_id')
        for store in stores:
            move_line = []
            move_line_vals = []
            for inv in invoices:
                if inv.pos_order_id.store_id.id == store.id:
                    pos_order = inv.pos_order_id
                    move_line.extend(pos_order.lines.filtered(lambda x: x.qty > 0).ids)
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
        summary_date = date.today() - timedelta(days=1)
        quantity = res.get('quantity')
        product_id = self.env['product.product'].browse(res.get('product_id'))
        price_unit = res.get('price_unit')

        synthetic_ids = []
        while quantity < 0:
            summary_date = summary_date - timedelta(days=1)
            synthetic_id = self.env['synthetic.account.move.pos'].search([
                ('invoice_date', '=', summary_date)
            ], limit=1)
            if not synthetic_id:
                synthetic_ids.append({
                    'product_id': product_id,
                    'quantity': abs(quantity),
                    'price_unit': price_unit,
                    'synthetic_id': False
                })
                quantity = 0
            else:
                lines = synthetic_id.line_ids.filtered(lambda x: x.product_id.barcode == product_id.barcode and
                                                      x.price_bkav == price_unit)
                if len(lines) > 0:
                    sl = sum(lines.mapped('quantity'))
                    if quantity + sl <= 0:
                        synthetic_ids.append({
                            'product_id': product_id,
                            'quantity': sl,
                            'price_unit': price_unit,
                            'synthetic_id': synthetic_id.id
                        })
                        quantity += sl
                    else:
                        synthetic_ids.append({
                            'product_id': product_id,
                            'quantity': abs(quantity),
                            'price_unit': price_unit,
                            'synthetic_id': synthetic_id.id
                        })
                        quantity = 0
        return synthetic_ids

    def make_adjusted_invoice_pos(self, vals_neg):
        record_ids = []
        for data_store in vals_neg:
            summary_return_line_id = self.env['summary.account.move.pos.return.line'].browse(data_store.get('return_line_id'))
            pos_order_return_ids = summary_return_line_id.invoice_ids
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
                            }
                        })
                    else:
                        quantity = products.get(item).get('quantity')
                        products.get(item).update({
                            'quantity': quantity + pos_order_line.get('quantity'),
                        })
                lines = []
                for item in products:
                    lines.append((0, 0, {
                        'product_id': products.get(item).get('product_id'),
                        'quantity': products.get(item).get('quantity'),
                        'price_unit': products.get(item).get('price_unit'),
                        'invoice_ids': [(6, 0, pos_order_return_ids.ids)]
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
    """

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
