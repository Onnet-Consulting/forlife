# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date
from .utils import genarate_pos_code


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

    line_discount_ids = fields.One2many('summary.account.move.pos.line.discount', compute="_compute_line_discount")

    def _compute_line_discount(self):
        for r in self:
            r.line_discount_ids = self.env["summary.account.move.pos.line.discount"].search([
                ('summary_id', '=', r.id)
            ])

    def get_line_discount_detail(self, line):
        item = {
            "line_pk": line.get_pk_synthetic_line_discount(),
            "price_unit": line.price_subtotal,
            "price_unit_incl": line.price_subtotal_incl,
            "tax_ids": line.tax_ids_after_fiscal_position.ids,
            "promotion_type": line.promotion_type,
            "amount_total": line.price_subtotal_incl,
        }
        return item

    def get_line_discount(self, line):
        line_discount_details = line.order_id.lines.filtered(
            lambda r: r.is_promotion == True and r.promotion_type in ['card','point']
        )
        items = []
        if line_discount_details:
            for line_discount_detail in line_discount_details:
                item = self.get_line_discount_detail(line_discount_detail)
                items.append((0,0,item))
        return items


    def get_move_line(self, line):
        line_discount_item = self.get_line_discount(line)
        item = {
            "product_id": line.product_id.id,
            "quantity": line.qty,
            "price_unit": line.price_unit_excl,
            "price_unit_incl": line.price_unit_incl,
            "x_free_good": line.is_reward_line,
            "invoice_ids": [line.order_id.id],
            "tax_ids": line.tax_ids_after_fiscal_position.ids,
            "line_ids": line_discount_item,
        }
        return item

    def include_line_by_product_and_price_bkav(self, lines):
        items = {}

        for line in lines:
            pk = line.get_pk_synthetic()
            item = self.get_move_line(line)
            item["line_pk"] = pk
            if items.get(pk):
                row = items[pk]
                row["quantity"] += item["quantity"]
                row["invoice_ids"].extend(item["invoice_ids"])
                row["invoice_ids"] = list(set(row["invoice_ids"]))
                row["line_ids"].extend(item["line_ids"])
                # row["tax_ids"].extend(item["tax_ids"])
                # row["tax_ids"] = list(set(row["tax_ids"]))
                items[pk] = row
            else:
                items[pk] = item

        return items


    def recursive_move_line_items(
        self,
        items={},
        lines=[],
        store=None,
        page=0,
        company_id=None
    ):
        model_code = genarate_pos_code(store_id=store, index=page)
        first_n=0
        last_n=1000
        pk = f"{store.id}_{page}"
        if len(lines) > last_n:
            separate_lines = lines[first_n:last_n]
            del lines[first_n:last_n]

            items[pk] = {
                'code': model_code,
                'company_id': company_id.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': separate_lines
            }
            page += 1
            self.recursive_move_line_items(
                items=items, 
                lines=lines, 
                store=store, 
                page=page, 
                company_id=company_id
            )
        else:
            items[pk] = {
                'code': model_code,
                'company_id': company_id.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': lines
            }

    def get_items(self, *args, **kwargs):
        model = self.env['summary.account.move.pos']
        model_line = self.env['summary.account.move.pos.line']

        last_day = date.today()

        domain = [
            ('is_general', '=', False),
            ('is_post_bkav_store', '=', True),
            ('exists_bkav', '=', False),
            ('pos_order_id', '!=', False),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        

        if not kwargs.get("env"):
            domain.append(('invoice_date', '<', last_day))

        move_ids = self.env['account.move'].search(domain)
        # .filtered(
        #     lambda r: r.pos_order_id.store_id.is_post_bkav == True
        # )
        # pos_order = self.env['pos.order'].search(domain)

        lines = self.env['pos.order.line'].search([
            ('order_id', 'in', move_ids.mapped("pos_order_id").ids),
            ('refunded_orderline_id', '=', False),
            ('qty', '>', 0),
            ('is_promotion', '=', False)
        ])

        data = {}
        items = {}
        pos_order_synthetic = None
        res_pos = None

        if lines:
            pos_order_synthetic = lines.mapped("order_id")
            stores = pos_order_synthetic.mapped("store_id")
            
            for store in stores:
                res = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
                line_items = self.include_line_by_product_and_price_bkav(res)
                self.recursive_move_line_items(
                    items=items,
                    lines=list(line_items.values()),
                    store=store,
                    page=0,
                    company_id=res[0].company_id
                )
                data[store.id] = line_items


            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res_pos = model.create(vals_list)

        return data, res_pos, move_ids


    def include_line_by_product(self, lines):
        pos_order = lines.mapped("order_id")
        stores = pos_order.mapped("store_id")
        data = {}
        company_ids = {}
        for store in stores:
            exits_products = {}
            lines_store = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
            items = {}
            for line in lines:
                if not line.product_id.barcode:
                    continue

                pk = f"{line.product_id.barcode}_{float(line.price_unit)}"
                if items.get(pk):
                    item = items[pk]
                    invoice_ids = item["invoice_ids"]
                    invoice_ids.append(line.order_id.id)
                    item["quantity"] += line.qty
                    item["invoice_ids"] = list(set(invoice_ids))
                else:
                    items[pk] = {
                        "product_id": line.product_id.id,
                        "quantity": line.qty,
                        "price_unit": line.price_bkav,
                        "invoice_ids": [line.order_id.id]
                    }
            data[store.id] = items
            company_ids[store.id] = lines_store[0].company_id.id

        return stores, data, company_ids


    def recursive_move_items(
        self, 
        items={},
        stores={},
        store_id=0,
        lines=[],
        page=0,
        company_ids={}
    ):
        store = stores.get(store_id)
        company_id = company_ids.get(store_id)
        first = 0
        last = 1000
        pk = f"{store_id}_{page}"
        pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
        if len(lines) > 1000:
            separate_lines = lines[first:last]
            del lines[first:last]
            items[pk] = {
                'code': pos_license_bkav,
                'company_id': company_id.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': separate_lines
            }
            page += 1
            self.recursive_move_items(
                items=items,
                stores=stores,
                store_id=store_id,
                lines=lines,
                page=page,
                company_ids=company_ids
            )
        else:
            items[pk] = {
                'code': pos_license_bkav,
                'company_id': company_id.id,
                'store_id': store.id,
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': lines
            }

    def collect_invoice_balance_clearing(self, records, store_data, company_ids):
        items = {}
        model = self.env['synthetic.account.move.pos']
        model_line = self.env['synthetic.account.move.pos.line']
        for k, v in records.items():
            self.recursive_move_items(
                items=items,
                stores=store_data,
                store_id=k,
                lines=v,
                page=0,
                company_ids=company_ids
            )

        for k, v in items.items():
            res_line = model_line.create(v["line_ids"])
            v["line_ids"] = res_line.ids

        vals_list = list(items.values())

        res = model.create(vals_list)


    def collect_invoice_difference(self, records, store_data, company_ids):
        model = self.env['summary.adjusted.invoice.pos']
        model_line = self.env['summary.adjusted.invoice.pos.line']

        vals_list = []
        for store_id, lines in records.items():
            store = store_data[store_id]
            company_id = company_ids[store_id]
            i = 0
            for k, v in lines.items():
                res_line = model_line.create(v)
                pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                vals_list.append({
                    'code': pos_license_bkav,
                    'company_id': company_id.id,
                    'store_id': store.id,
                    'partner_id': store.contact_id.id,
                    'invoice_date': date.today(),
                    'line_ids': res_line.ids,
                    'source_invoice': k if k != 'adjusted' else None,
                })
                i += 1
        res = model.create(vals_list)


    def create_an_invoice_bkav(self):
        synthetic_account_move = self.env['synthetic.account.move.pos'].search([('exists_bkav', '=', False)])
        synthetic_account_move.create_an_invoice()

        adjusted_move = self.env['summary.adjusted.invoice.pos'].search([
            ('exists_bkav', '=', False),
            ('source_invoice', '!=', False)
        ])
        adjusted_move.create_an_invoice()

    def handle_invoice_balance_clearing(
        self, 
        matching_records,
        move_pos_line, 
        move_refund_pos_line, 
        v,
        sale_data,
        store_id
        ):
        line_pk = sale_data["line_pk"]
        summary_line_id = move_pos_line.filtered(
            lambda r: r.summary_id.store_id.id == store_id \
            and r.line_pk == line_pk
        )
        return_line_id = move_refund_pos_line.filtered(
            lambda r: r.return_id.store_id.id == store_id \
            and r.line_pk == line_pk
        )

        sale_data["line_ids"].extend(v["line_ids"])

        sale_data["quantity"] += v["quantity"]
        sale_data["remaining_quantity"] = sale_data["quantity"]
        sale_data["summary_line_id"] = summary_line_id[0].id if summary_line_id else None
        sale_data["return_line_id"] = return_line_id[0].id if return_line_id else None
        if matching_records.get(store_id):
            matching_records[store_id].append(sale_data)
        else:
            matching_records[store_id] = [sale_data]

    def handle_invoice_difference(
        self, 
        remaining_records,
        synthetic_lines,
        v,
        store_id
    ):
        is_adjusted = False
        if synthetic_lines:
            line_pk = v["line_pk"]
            lines = synthetic_lines.filtered(
                lambda r: r.synthetic_id.store_id.id == store_id and \
                r.line_pk == line_pk and abs(r.remaining_quantity) >= abs(v["quantity"])
            )
            if lines:
                line = lines[0]
                row = v
                # for line in lines:
                #     row = v
                #     if abs(line.remaining_quantity) >= abs(v["quantity"]):
                row["quantity"] = abs(row["quantity"])
                row["price_unit"] = -abs(row["price_unit"])
                row["price_unit_incl"] = -abs(row["price_unit_incl"])
                adjusted_quantity = line.adjusted_quantity + abs(v["quantity"])
                remaining_quantity = line.remaining_quantity - abs(v["quantity"])
                if remaining_records.get(store_id):
                    rows = remaining_records[store_id]
                    if rows.get(line.synthetic_id.id):
                        rows[line.synthetic_id.id].append(row)
                    else:
                        rows[line.synthetic_id.id] = [row]
                else:
                    remaining_records[store_id] = {line.synthetic_id.id: [row]}
                line.with_delay(
                    description="Adjusted invoice for POS and Nhanh.vn", channel="root.NhanhMQ"
                ).write({
                    "remaining_quantity": remaining_quantity,
                    "adjusted_quantity": adjusted_quantity
                })
                is_adjusted = True
                        # break
                    # else:
                    #     row["quantity"] = abs(line.remaining_quantity)
                    #     v["quantity"] += line.remaining_quantity
                    #     adjusted_quantity = line.adjusted_quantity + abs(line.remaining_quantity)
                    #     row["price_unit"] = -abs(row["price_unit"])
                    #     if remaining_records.get(store_id):
                    #         rows = remaining_records[store_id]
                    #         if rows.get(line.synthetic_id.id):
                    #             rows[line.synthetic_id.id].append(row)
                    #         else:
                    #             rows[line.synthetic_id.id] = [row]
                    #     else:
                    #         remaining_records[store_id] = {line.synthetic_id.id: [row]}
                    #     line.sudo().with_delay(
                    #         description="Adjusted invoice for POS", channel="root.NhanhMQ"
                    #     ).write({
                    #         "remaining_quantity": 0,
                    #         "adjusted_quantity": adjusted_quantity
                    #     })
            # else:
            #     row = v
            #     row["quantity"] = abs(row["quantity"])
            #     row["price_unit"] = -abs(row["price_unit"])
            #     if remaining_records.get(store_id):
            #         rows = remaining_records[store_id]
            #         if rows.get('adjusted'):
            #             rows['adjusted'].append(row)
            #         else:
            #             rows['adjusted'] = [row]
            #     else:
            #         remaining_records[store_id] = {'adjusted': [row]}
        if not is_adjusted:
            row = v
            row["quantity"] = abs(row["quantity"])
            row["price_unit"] = -abs(row["price_unit"])
            row["price_unit_incl"] = -abs(row["price_unit_incl"])
            if remaining_records.get(store_id):
                rows = remaining_records[store_id]
                if rows.get('adjusted'):
                    rows['adjusted'].append(row)
                else:
                    rows['adjusted'] = [row]
            else:
                remaining_records[store_id] = {'adjusted': [row]}


    def cronjob_collect_invoice_to_bkav_end_day(self, *args, **kwargs):
        self.collect_invoice_to_bkav_end_day(*args, **kwargs)
        self.create_an_invoice_bkav()


    def collect_invoice_to_bkav_end_day(self, *args, **kwargs):
        synthetic_lines = self.env['synthetic.account.move.pos.line'].search([
            ('remaining_quantity', '>', 0),
            ('synthetic_id', '!=', False),
            ('exists_bkav', '=', True)
        ], order="invoice_date desc")


        sales, sale_res, sale_synthetic = self.env['summary.account.move.pos'].get_items(*args, **kwargs)
        refunds, refund_res, refund_synthetic = self.env['summary.account.move.pos.return'].get_items(*args, **kwargs)
        matching_records = {}
        remaining_records = {}

        store_data = {}
        company_ids = {}
        if len(refunds.keys()):
            move_refund_pos_line = refund_res.line_ids
            for store_id, refund in refunds.items():
                res_store = refund_res.filtered(lambda r: r.store_id.id == store_id)
                store_data[store_id] = res_store[0].store_id
                company_ids[store_id] = res_store[0].company_id
                if sales.get(store_id):
                    move_pos_line = sale_res.line_ids
                    sale = sales[store_id]
                    for k, v in refund.items():
                        if sale.get(k):
                            sale_data = sale.pop(k)
                            if abs(sale_data["quantity"]) > abs(v["quantity"]):
                                self.handle_invoice_balance_clearing(
                                    matching_records,
                                    move_pos_line,
                                    move_refund_pos_line,
                                    v,
                                    sale_data,
                                    store_id
                                )
                            elif abs(sale_data["quantity"]) < abs(v["quantity"]):
                                self.handle_invoice_difference(
                                    remaining_records,
                                    synthetic_lines,
                                    v,
                                    store_id
                                )
                        else:
                            self.handle_invoice_difference(
                                remaining_records,
                                synthetic_lines,
                                v,
                                store_id
                            )
                    if len(sale.keys()):
                        sales[store_id] = sale
                    else:
                        sales.pop(store_id)
                else:
                    for k, v in refund.items():
                        self.handle_invoice_difference(
                            remaining_records,
                            synthetic_lines,
                            v,
                            store_id
                        )
        if len(sales.keys()):
            move_pos_line = sale_res.line_ids
            for store_id, sale in sales.items():
                res_store = sale_res.filtered(lambda r: r.store_id.id == store_id)
                store_data[store_id] = res_store[0].store_id
                company_ids[store_id] = res_store[0].company_id

                if len(sale.keys()):
                    for k, v in sale.items():
                        line_pk = v["line_pk"]
                        summary_line_id = move_pos_line.filtered(
                            lambda r: r.summary_id.store_id.id == store_id \
                            and r.line_pk == line_pk
                        )
                        v["remaining_quantity"] = v["quantity"]
                        v["summary_line_id"] = summary_line_id[0].id
                        v["return_line_id"] = None

                        if matching_records.get(store_id):
                            matching_records[store_id].append(v)
                        else:
                            matching_records[store_id] = [v]

        self.collect_invoice_balance_clearing(matching_records, store_data, company_ids)
        self.collect_invoice_difference(remaining_records, store_data, company_ids)


        if sale_synthetic:
            sale_synthetic.update({"is_general": True})
        if refund_synthetic:
            refund_synthetic.update({"is_general": True})
        
        return True


class SummaryAccountMovePosLine(models.Model):
    _name = 'summary.account.move.pos.line'

    line_pk = fields.Char('Line primary key')
    summary_id = fields.Many2one('summary.account.move.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="compute_price_subtotal")
    amount_total = fields.Monetary('Thành tiền', compute="compute_amount_total")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')
    line_ids = fields.One2many('summary.account.move.pos.line.discount', 'summary_line_id')

    def __str__(self):
        return f"{self.summary_id.code} - {self.barcode}"

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = r.price_unit * r.quantity - r.discount_amount

    @api.depends('price_subtotal', 'tax_amount', 'price_unit_incl')
    def compute_amount_total(self):
        for r in self:
            r.amount_total = r.price_unit_incl *  r.quantity - r.discount_amount

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

class SummaryAccountMovePosLineDiscount(models.Model):
    _name = 'summary.account.move.pos.line.discount'

    line_pk = fields.Char('Line primary key')
    summary_line_id = fields.Many2one('summary.account.move.pos.line')
    summary_id = fields.Many2one('summary.account.move.pos', related="summary_line_id.summary_id")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    amount_total = fields.Monetary('Thành tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    promotion_type = fields.Selection(
        selection=[
            ('point', 'Point'),
            ('card', 'Card'),
        ],
        string='Promotion Type', index=True, readonly=True
    )

    @api.depends('tax_ids', 'price_unit')
    def compute_tax_amount(self):
        for r in self:
            if r.tax_ids:
                tax_amount = 0
                for tax in r.tax_ids:
                    tax_amount += (r.price_unit * tax.amount) / 100
                r.tax_amount = tax_amount
            else:
                r.tax_amount = 0

    # @api.depends('price_unit', 'tax_amount')
    # def compute_amount_total(self):
    #     for r in self:
    #         r.amount_total = r.price_unit + r.tax_amount