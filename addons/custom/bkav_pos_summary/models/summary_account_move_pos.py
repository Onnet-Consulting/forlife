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

    line_discount_ids = fields.One2many(
        'summary.account.move.pos.line.discount', 
        compute="_compute_line_discount"
    )
    discount_ids = fields.One2many('summary.account.move.pos.line.discount', compute="_compute_line_discount")

    @api.model
    def _compute_line_discount(self):
        for r in self:
            r.line_discount_ids = self.env["summary.account.move.pos.line.discount"].search([
                ('summary_id', '=', r.id)
            ])
            r.discount_ids = self.env["summary.account.move.pos.line.discount"].search([
                ('summary_ids', 'in', [r.id]),
                ('summary_line_id', '=', False),
                ('store_id', '=', r.store_id.id)
            ])

    def get_line_discount_detail(self, line):
        item = {
            "line_pk": line.get_pk_synthetic_line_discount(),
            "price_unit": line.price_subtotal,
            "price_unit_incl": line.price_subtotal_incl,
            "tax_ids": line.tax_ids_after_fiscal_position.ids,
            "promotion_type": line.promotion_type,
            "amount_total": line.price_subtotal_incl,
            "invoice_ids": [line.order_id.id],
        }
        return item

    def get_line_discount(self, line, discount_items):
        line_discount_details = line.order_id.lines.filtered(
            lambda r: r.is_promotion == True and r.promotion_type in ['card','point'] and r.product_src_id.id == line.id
        )

        items = []

        if line_discount_details:
            for line_discount_detail in line_discount_details:
                item = self.get_line_discount_detail(line_discount_detail)
                line_pk = f'{item["promotion_type"]}_{item["line_pk"]}'
                if discount_items.get(line_pk):
                    row = discount_items[line_pk]
                    row["price_unit"] += item["price_unit"]
                    row["price_unit_incl"] += item["price_unit_incl"]
                    row["amount_total"] += item["amount_total"]
                else:
                    discount_items[line_pk] = item.copy()
                    discount_items[line_pk]["line_pk"] = line_pk

                items.append((0,0,item))
        return items


    def get_move_line(self, line, discount_items):
        line_ids = self.get_line_discount(line, discount_items)
        item = {
            "product_id": line.product_id.id,
            "quantity": line.qty,
            "price_unit": line.price_unit_excl,
            "price_unit_incl": line.price_unit_incl,
            "x_free_good": line.is_reward_line,
            "invoice_ids": [line.order_id.id],
            "tax_ids": line.tax_ids_after_fiscal_position.ids,
            "line_ids": line_ids,
        }
        return item

    def include_line_by_product_and_price_bkav(self, lines):
        items = {}
        discount_items = {}
        for line in lines:
            if not line.product_id:
                continue
            if line.product_id.voucher or line.product_id.is_voucher_auto or line.product_id.is_product_auto:
                continue
            
            product_tmpl_id =  line.product_id.product_tmpl_id
            if product_tmpl_id.voucher or product_tmpl_id.is_voucher_auto or product_tmpl_id.is_product_auto:
                continue

            pk = line.get_pk_synthetic()
            item = self.get_move_line(line, discount_items)
            item["line_pk"] = pk
            if items.get(pk):
                row = items[pk]
                row["quantity"] += item["quantity"]
                row["invoice_ids"].extend(item["invoice_ids"])
                row["invoice_ids"] = list(set(row["invoice_ids"]))
                row["line_ids"].extend(item["line_ids"])
                items[pk] = row
            else:
                items[pk] = item

        return items, discount_items


    def recursive_move_line_items(
        self,
        items={},
        lines=[],
        store=None,
        page=0,
        limit=1000,
        company_id=None
    ):
        model_code = genarate_pos_code(store_id=store, index=page)
        first_n=0
        last_n=limit
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
                limit=limit,
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
        model_line_discount = self.env['summary.account.move.pos.line.discount']


        last_day = date.today()

        domain = [
            # ('is_general', '=', False),
            ('is_post_bkav_store', '=', True),
            ('exists_bkav', '=', False),
            ('pos_order_id', '!=', False),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        

        if not kwargs.get("env"):
            domain.append(('invoice_date', '<=', last_day))
        limit = 1000
        if kwargs.get("limit") and str(kwargs.get("limit")).isnumeric():
            limit = int(kwargs["limit"])

        move_ids = self.env['account.move'].search(domain)

        lines = self.env['pos.order.line'].search([
            ('order_id', 'in', move_ids.mapped("pos_order_id").ids),
            ('refunded_orderline_id', '=', False),
            ('qty', '>', 0),
            ('is_promotion', '=', False),
            ('is_general', '=', False),
            ('exists_bkav', '=', False),
        ])

        data = {}
        items = {}
        pos_order_synthetic = None
        res_pos = None
        store_discount_items = {}
        total_point = 0
        if lines:
            pos_order_synthetic = lines.mapped("order_id")
            stores = pos_order_synthetic.mapped("store_id")
            
            for store in stores:
                res = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
                total_point = sum(pos_order_synthetic.filtered(lambda r: r.store_id.id == store.id).mapped("total_point"))
                line_items, discount_items = self.include_line_by_product_and_price_bkav(res)
                self.recursive_move_line_items(
                    items=items,
                    lines=list(line_items.values()),
                    store=store,
                    page=0,
                    limit=limit,
                    company_id=res[0].company_id
                )
                data[store.id] = {
                    "items": line_items,
                    "total_point": total_point,
                    "card_point": discount_items
                }
                store_discount_items[store.id] = discount_items

            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res_pos = model.create(vals_list)

            discount_vals_list = []
            for k, v in store_discount_items.items():
                summary_ids = res_pos.filtered(lambda r: r.store_id.id == k)
                for pk, item in v.items():
                    v_item = item.copy()
                    v_item["summary_ids"] = summary_ids.ids
                    v_item["summary_line_id"] = None
                    v_item["store_id"] = k
                    discount_vals_list.append(v_item)
            

            model_line_discount.create(discount_vals_list)

        return data, res_pos, pos_order_synthetic


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
        limit=1000,
        company_ids={}
    ):
        store = stores.get(store_id)
        company_id = company_ids.get(store_id)
        first = 0
        last = limit
        pk = f"{store_id}_{page}"
        pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
        if len(lines) > last:
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
                limit=limit,
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

    def collect_invoice_balance_clearing(self, records, store_data, company_ids, limit):
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
                limit=limit,
                company_ids=company_ids
            )

        for k, v in items.items():
            res_line = model_line.create(v["line_ids"])
            v["line_ids"] = res_line.ids

        vals_list = list(items.values())

        res = model.create(vals_list)
        return res

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
        return res


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
        if abs(v["quantity"]) > 0:
            if synthetic_lines:
                line_pk = v["line_pk"]
                lines = synthetic_lines.filtered(
                    lambda r: r.synthetic_id.store_id.id == store_id and \
                    r.line_pk == line_pk
                )
                if lines:
                    # line = lines[0]
                    # row = v
                    for line in lines:
                        if abs(v["quantity"]) > 0:
                            row = v.copy()
                            if abs(line.remaining_quantity) >= abs(v["quantity"]):
                                row["quantity"] = -abs(row["quantity"])
                                row["price_unit"] = -abs(row["price_unit"])
                                row["price_unit_incl"] = -abs(row["price_unit_incl"])
                                row["synthetic_id"] = line.synthetic_id.id
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
                                v["quantity"] = 0
                                break
                            else:
                                row["quantity"] = -abs(line.remaining_quantity)
                                v["quantity"] -= abs(line.remaining_quantity)
                                adjusted_quantity = line.adjusted_quantity + abs(line.remaining_quantity)
                                row["price_unit"] = -abs(row["price_unit"])
                                row["synthetic_id"] = line.synthetic_id.id

                                if remaining_records.get(store_id):
                                    rows = remaining_records[store_id]
                                    if rows.get(line.synthetic_id.id):
                                        rows[line.synthetic_id.id].append(row)
                                    else:
                                        rows[line.synthetic_id.id] = [row]
                                else:
                                    remaining_records[store_id] = {line.synthetic_id.id: [row]}
                                line.sudo().with_delay(
                                    description="Adjusted invoice for POS", channel="root.NhanhMQ"
                                ).write({
                                    "remaining_quantity": 0,
                                    "adjusted_quantity": adjusted_quantity
                                })
                        else:
                            break
                    is_adjusted = True
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
                row = v.copy()
                row["quantity"] = -abs(row["quantity"])
                row["price_unit"] = -abs(row["price_unit"])
                row["price_unit_incl"] = -abs(row["price_unit_incl"])
                row["synthetic_id"] = None

                if remaining_records.get(store_id):
                    rows = remaining_records[store_id]
                    if rows.get('adjusted'):
                        rows['adjusted'].append(row)
                    else:
                        rows['adjusted'] = [row]
                else:
                    remaining_records[store_id] = {'adjusted': [row]}


    def create_an_invoice_bkav(self):
        synthetic_account_move = self.with_context({"lang": "vi_VN"}).env['synthetic.account.move.pos'].search([('exists_bkav', '=', False)])
        synthetic_account_move.create_an_invoice()

        adjusted_move = self.with_context({"lang": "vi_VN"}).env['summary.adjusted.invoice.pos'].search([
            ('exists_bkav', '=', False),
            ('source_invoice', '!=', False)
        ])
        adjusted_move.create_an_invoice()


    def cronjob_collect_invoice_to_bkav_end_day(self, *args, **kwargs):
        self.collect_invoice_to_bkav_end_day(*args, **kwargs)
        self.create_an_invoice_bkav()

    def cronjob_get_all_invoice_info(self):
        synthetic_account_move = self.with_context({"lang": "vi_VN"}).env['synthetic.account.move.pos'].search([('exists_bkav', '=', True)])
        synthetic_account_move.get_invoice_bkav()

        adjusted_move = self.with_context({"lang": "vi_VN"}).env['summary.adjusted.invoice.pos'].search([
            ('exists_bkav', '=', True),
            ('source_invoice', '!=', False)
        ])
        adjusted_move.get_invoice_bkav()


    def handle_accumulate_point_focus_card(
        self, 
        data,
        synthetics,
        adjusteds,
        synthetic_line_discounts,
        synthetic_accumulates,
        store_data,
        company_ids
    ):
        matching_discounts = []
        remaining_discounts = []
        matching_accumulates = []
        remaining_accumulates = []
        vals_list = {}

        for store_id, item in data.items():
            card_grade_focus = item["card_grade_focus"]
            accumulate_point = item["accumulate_point"]
            store_synthetics = synthetics.filtered(lambda r: r.store_id.id == store_id)
            store_adjusteds = adjusteds.filtered(lambda r: r.store_id.id == store_id)
            store = store_data[store_id]
            company_id = company_ids[store_id]

            for k, v in card_grade_focus.items():
                v_item = v.copy()
                if v_item["amount_total"] < 0:
                    v_item["synthetic_ids"] = store_synthetics.ids if store_synthetics else []
                    v_item["bkav_synthetic_id"] = store_synthetics[0].id if store_synthetics else None
                    v_item["store_id"] = store_id
                    v_item["synthetic_line_id"] = None
                    v_item["remaining_amount_total"] = v_item["amount_total"]
                    matching_discounts.append(v_item)
                else:
                    v_item["adjusted_ids"] = store_adjusteds.ids if store_adjusteds else []
                    v_item["store_id"] = store_id
                    v_item["adjusted_line_id"] = None
                    lines = synthetic_line_discounts.filtered(lambda r: r.store_id.id == store_id and r.line_pk == k)
                    if lines:
                        for line in lines:
                            if abs(v_item["amount_total"]) > 0:
                                store_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice.id == line.bkav_synthetic_id.id)
                                if abs(line.remaining_amount_total) >= abs(v_item["amount_total"]):
                                    remaining_amount_total = line.remaining_amount_total + v_item["amount_total"]
                                    adjusted_amount_total = line.adjusted_amount_total + v_item["amount_total"]
                                    if store_adjusted:
                                        v_item["bkav_adjusted_id"] = store_adjusted.id
                                        remaining_discounts.append(v_item.copy())
                                    else:
                                        if vals_list.get(line.bkav_synthetic_id.id):
                                            row = vals_list[line.bkav_synthetic_id.id]
                                            row["adjusted_discount_ids"].append((0,0, v_item.copy()))
                                        else:
                                            pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                            vals_list[line.bkav_synthetic_id.id] = {
                                                'code': pos_license_bkav,
                                                'company_id': company_id.id,
                                                'store_id': store.id,
                                                'partner_id': store.contact_id.id,
                                                'invoice_date': date.today(),
                                                'line_ids': [],
                                                'source_invoice': line.bkav_synthetic_id.id,
                                                'accumulate_ids': [],
                                                'adjusted_discount_ids': [(0,0, v_item.copy())],
                                            }
                                    line.sudo().with_delay(
                                        description="Adjusted invoice for POS", channel="root.NhanhMQ"
                                    ).write({
                                        "remaining_amount_total": remaining_amount_total,
                                        "adjusted_amount_total": adjusted_amount_total
                                    })
                                    v_item["amount_total"] = 0
                                    break
                                else:
                                    v_item["amount_total"] -= abs(line.remaining_amount_total)
                                    adjusted_amount_total = line.adjusted_amount_total + abs(line.remaining_amount_total)
                                    v_item_copy = v_item.copy()
                                    v_item_copy["price_unit_incl"] = v_item_copy["amount_total"] = abs(line.remaining_amount_total)
                                    tax_results = line.get_amount_total(v_item_copy["price_unit_incl"])
                                    v_item_copy["price_unit"] = tax_results["total_excluded"]

                                    if store_adjusted:
                                        v_item_copy["bkav_adjusted_id"] = store_adjusted.id
                                        remaining_discounts.append(v_item_copy)
                                    else:
                                        if vals_list.get(line.bkav_synthetic_id.id):
                                            row = vals_list[line.bkav_synthetic_id.id]
                                            row["adjusted_discount_ids"].append((0,0, v_item_copy))
                                        else:
                                            pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                            vals_list[line.bkav_synthetic_id.id] = {
                                                'code': pos_license_bkav,
                                                'company_id': company_id.id,
                                                'store_id': store.id,
                                                'partner_id': store.contact_id.id,
                                                'invoice_date': date.today(),
                                                'line_ids': [],
                                                'source_invoice': line.bkav_synthetic_id.id,
                                                'accumulate_ids': [],
                                                'adjusted_discount_ids': [(0,0, v_item_copy)],
                                            }
                                    line.sudo().with_delay(
                                        description="Adjusted invoice for POS", channel="root.NhanhMQ"
                                    ).write({
                                        "remaining_amount_total": 0,
                                        "adjusted_amount_total": adjusted_amount_total
                                    })
                            else:
                                break

                        if v_item["amount_total"] > 0:
                            not_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice == False)
                            if not_adjusted:
                                v_item["bkav_adjusted_id"] = not_adjusted[0].id if not_adjusted else None
                                remaining_discounts.append(v_item.copy())
                            else:
                                if vals_list.get('adjusted'):
                                    row = vals_list['adjusted']
                                    row["adjusted_discount_ids"].append((0,0, v_item.copy()))
                                else:
                                    pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                    vals_list['adjusted'] = {
                                        'code': pos_license_bkav,
                                        'company_id': company_id.id,
                                        'store_id': store.id,
                                        'partner_id': store.contact_id.id,
                                        'invoice_date': date.today(),
                                        'line_ids': [],
                                        'source_invoice': None,
                                        'accumulate_ids': [],
                                        'adjusted_discount_ids': [(0,0, v_item.copy())],
                                    }
                    else:
                        not_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice == False)
                        if not_adjusted:
                            v_item["bkav_adjusted_id"] = not_adjusted[0].id if not_adjusted else None
                            remaining_discounts.append(v_item.copy())
                        else:
                            if vals_list.get('adjusted'):
                                row = vals_list['adjusted']
                                row["adjusted_discount_ids"].append((0,0, v_item.copy()))
                            else:
                                pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                vals_list['adjusted'] = {
                                    'code': pos_license_bkav,
                                    'company_id': company_id.id,
                                    'store_id': store.id,
                                    'partner_id': store.contact_id.id,
                                    'invoice_date': date.today(),
                                    'line_ids': [],
                                    'source_invoice': None,
                                    'accumulate_ids': [],
                                    'adjusted_discount_ids': [(0,0, v_item.copy())],
                                }
            if accumulate_point > 0:
                matching_accumulates.append({
                    "total_point": accumulate_point,
                    "remaining_total_point": accumulate_point,
                    "synthetic_ids": store_synthetics.ids if store_synthetics else [],
                    "bkav_synthetic_id": store_synthetics[0].id if store_synthetics else None,
                    "store_id": store_id
                })
            elif accumulate_point < 0:
                lines = synthetic_accumulates.filtered(lambda r: r.store_id.id == store_id)
                if lines:
                    for line in lines:
                        if abs(accumulate_point) > 0:
                            store_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice.id == line.bkav_synthetic_id.id)
                            if abs(line.remaining_total_point) >= abs(accumulate_point):
                                remaining_total_point = line.remaining_total_point + accumulate_point
                                adjusted_quantity = line.adjusted_total_point + accumulate_point
                                accumulate_item = {
                                    "total_point": accumulate_point,
                                    "adjusted_ids": store_adjusteds.ids if store_adjusteds else [],
                                    "store_id": store_id
                                }
                                if store_adjusted:
                                    accumulate_item["bkav_adjusted_id"] = store_adjusted.id
                                    remaining_accumulates.append(accumulate_item)
                                else:
                                    if vals_list.get(line.bkav_synthetic_id.id):
                                        row = vals_list[line.bkav_synthetic_id.id]
                                        row["accumulate_ids"].append((0,0, accumulate_item))
                                    else:
                                        pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                        vals_list[line.bkav_synthetic_id.id] = {
                                            'code': pos_license_bkav,
                                            'company_id': company_id.id,
                                            'store_id': store.id,
                                            'partner_id': store.contact_id.id,
                                            'invoice_date': date.today(),
                                            'line_ids': [],
                                            'source_invoice': line.bkav_synthetic_id.id,
                                            'accumulate_ids': [(0,0, accumulate_item)],
                                            'adjusted_discount_ids': []
                                        }

                                line.sudo().with_delay(
                                    description="Adjusted invoice for POS", channel="root.NhanhMQ"
                                ).write({
                                    "remaining_total_point": remaining_total_point,
                                    "adjusted_total_point": adjusted_quantity
                                })
                                accumulate_point = 0
                                break
                            else:
                                accumulate_point += abs(line.remaining_total_point)
                                adjusted_quantity = line.adjusted_total_point - abs(line.remaining_total_point)
                                accumulate_item = {
                                    "total_point": -abs(line.remaining_total_point),
                                    "adjusted_ids": store_adjusteds.ids if store_adjusteds else [],
                                    "store_id": store_id
                                }

                                if store_adjusted:
                                    accumulate_item["bkav_adjusted_id"] = store_adjusted.id
                                    remaining_accumulates.append(accumulate_item)
                                else:
                                    if vals_list.get(line.bkav_synthetic_id.id):
                                        row = vals_list[line.bkav_synthetic_id.id]
                                        row["accumulate_ids"].append((0,0, accumulate_item))
                                        vals_list[line.bkav_synthetic_id.id] = row
                                    else:
                                        pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                        vals_list[line.bkav_synthetic_id.id] = {
                                            'code': pos_license_bkav,
                                            'company_id': company_id.id,
                                            'store_id': store.id,
                                            'partner_id': store.contact_id.id,
                                            'invoice_date': date.today(),
                                            'line_ids': [],
                                            'source_invoice': line.bkav_synthetic_id.id,
                                            'accumulate_ids': [(0,0, accumulate_item)]
                                        }

                                line.sudo().with_delay(
                                    description="Adjusted invoice for POS", channel="root.NhanhMQ"
                                ).write({
                                    "remaining_total_point": 0,
                                    "adjusted_total_point": adjusted_quantity
                                })
                        else:
                            break

                    if accumulate_point < 0:
                        not_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice == False)
                        accumulate_item = {
                            "total_point": accumulate_point,
                            "adjusted_ids": store_adjusteds.ids if store_adjusteds else [],
                            "store_id": store_id,
                        }
                        if not_adjusted:
                            accumulate_item["bkav_adjusted_id"] = not_adjusted[0].id if not_adjusted else None
                            remaining_accumulates.append(accumulate_item)
                        else:
                            if vals_list.get('adjusted'):
                                row = vals_list['adjusted']
                                row["accumulate_ids"].append((0,0, accumulate_item))
                                vals_list['adjusted'] = row
                            else:
                                pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                                vals_list['adjusted'] = {
                                    'code': pos_license_bkav,
                                    'company_id': company_id.id,
                                    'store_id': store.id,
                                    'partner_id': store.contact_id.id,
                                    'invoice_date': date.today(),
                                    'line_ids': [],
                                    'source_invoice': None,
                                    'accumulate_ids': [(0,0, accumulate_item)]
                                }
                else:
                    not_adjusted = store_adjusteds.filtered(lambda r: r.source_invoice == False)
                    accumulate_item = {
                        "total_point": accumulate_point,
                        "adjusted_ids": store_adjusteds.ids if store_adjusteds else [],
                        "store_id": store_id,
                    }
                    if not_adjusted:
                        accumulate_item["bkav_adjusted_id"] = not_adjusted[0].id if not_adjusted else None
                        remaining_accumulates.append(accumulate_item)
                    else:
                        if vals_list.get('adjusted'):
                            row = vals_list['adjusted']
                            row["accumulate_ids"].append((0,0, accumulate_item))
                            vals_list['adjusted'] = row
                        else:
                            pos_license_bkav = self.env['ir.sequence'].next_by_code('pos.license.bkav')
                            vals_list['adjusted'] = {
                                'code': pos_license_bkav,
                                'company_id': company_id.id,
                                'store_id': store.id,
                                'partner_id': store.contact_id.id,
                                'invoice_date': date.today(),
                                'line_ids': [],
                                'source_invoice': None,
                                'accumulate_ids': [(0,0, accumulate_item)]
                            }

        self.env["synthetic.account.move.pos.line.discount"].create(matching_discounts)
        self.env["summary.adjusted.invoice.pos.line.discount"].create(remaining_discounts)

        self.env["synthetic.accumulate.point"].create(matching_accumulates)
        self.env["adjusted.accumulate.point"].create(remaining_accumulates)
        self.env['summary.adjusted.invoice.pos'].create(list(vals_list.values()))


    def get_original_invoice(self):
        synthetic_lines = self.env['synthetic.account.move.pos.line'].search([
            ('remaining_quantity', '>', 0),
            ('synthetic_id', '!=', False),
            ('exists_bkav', '=', True)
        ], order="invoice_date desc, id desc")

        synthetic_line_discounts = self.env['synthetic.account.move.pos.line.discount'].search([
            ('remaining_amount_total', '<', 0),
            ('bkav_synthetic_id', '!=', False),
            ('exists_bkav', '=', True)
        ], order="invoice_date desc, id desc")


        synthetic_accumulates = self.env['synthetic.accumulate.point'].search([
            ('remaining_total_point', '>', 0),
            ('bkav_synthetic_id', '!=', False),
            ('exists_bkav', '=', True)
        ], order="invoice_date desc, id desc")

        return synthetic_lines, synthetic_line_discounts, synthetic_accumulates


    def collect_invoice_to_bkav_end_day(self, *args, **kwargs):
        synthetic_lines, synthetic_line_discounts, synthetic_accumulates = self.get_original_invoice()
        limit = 1000
        if kwargs.get("limit") and str(kwargs.get("limit")).isnumeric():
            limit = int(kwargs["limit"])


        sales, sale_res, sale_synthetic = self.env['summary.account.move.pos'].get_items(*args, **kwargs)
        refunds, refund_res, refund_synthetic = self.env['summary.account.move.pos.return'].get_items(*args, **kwargs)
        matching_records = {}
        remaining_records = {}

        store_data = {}
        company_ids = {}
        data = {}
        store_ids = set(list(sales.keys()) + list(refunds.keys()))

        for store_id in store_ids:
            accumulate_point = 0
            if refunds.get(store_id):
                move_refund_pos_line = refund_res.line_ids
                refund = refunds[store_id]["items"]
                res_store = refund_res.filtered(lambda r: r.store_id.id == store_id)
                store_data[store_id] = res_store[0].store_id
                company_ids[store_id] = res_store[0].company_id
                refund_card_grade_focus = refunds[store_id]["card_point"]

                if sales.get(store_id):
                    accumulate_point = sales[store_id]["total_point"] - refunds[store_id]["total_point"]
                    card_grade_focus = sales[store_id]["card_point"]
                    for line_pk, item in refund_card_grade_focus.items():
                        if card_grade_focus.get(line_pk):
                            row = card_grade_focus[line_pk]
                            row["price_unit"] += item["price_unit"]
                            row["price_unit_incl"] += item["price_unit_incl"]
                            row["amount_total"] += item["amount_total"]
                            card_grade_focus[line_pk] = row
                        else:
                            card_grade_focus[line_pk] = item

                    move_pos_line = sale_res.line_ids
                    sale = sales[store_id]["items"]
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
                                v["quantity"] = abs(v["quantity"]) - abs(sale_data["quantity"])
                                self.handle_invoice_difference(
                                    remaining_records,
                                    synthetic_lines,
                                    v,
                                    store_id
                                )
                        else:
                            v["quantity"] = abs(v["quantity"])
                            self.handle_invoice_difference(
                                remaining_records,
                                synthetic_lines,
                                v,
                                store_id
                            )
                    if len(sale.keys()):
                        sales[store_id]["items"] = sale
                    else:
                        sales[store_id].pop("items")
                else:
                    accumulate_point =- refunds[store_id]["total_point"]
                    card_grade_focus = refunds[store_id]["card_point"]

                    for k, v in refund.items():
                        v["quantity"] = abs(v["quantity"])
                        self.handle_invoice_difference(
                            remaining_records,
                            synthetic_lines,
                            v,
                            store_id
                        )
            elif sales.get(store_id):
                accumulate_point = sales[store_id]["total_point"]
                card_grade_focus = sales[store_id]["card_point"]

            data[store_id] = {
                "accumulate_point": accumulate_point,
                "card_grade_focus": card_grade_focus
            }


        if len(sales.keys()):
            move_pos_line = sale_res.line_ids
            for store_id in store_ids:
                if sales.get(store_id) and sales[store_id].get("items"):
                    sale = sales[store_id]["items"]
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

        synthetics = self.collect_invoice_balance_clearing(matching_records, store_data, company_ids, limit)
        adjusteds = self.collect_invoice_difference(remaining_records, store_data, company_ids)

        self.handle_accumulate_point_focus_card(
            data, 
            synthetics, 
            adjusteds, 
            synthetic_line_discounts, 
            synthetic_accumulates, 
            store_data, 
            company_ids
        )


        if sale_synthetic:
            sale_synthetic.update({"is_general": True})
            self.env["account.move"].search([('pos_order_id', 'in', sale_synthetic.ids)]).update({"is_general": True})
        if refund_synthetic:
            refund_synthetic.update({"is_general": True})
            self.env["account.move"].search([('pos_order_id', 'in', refund_synthetic.ids)]).update({"is_general": True})
        
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
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền', compute="_compute_amount")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')
    line_ids = fields.One2many('summary.account.move.pos.line.discount', 'summary_line_id')

    def get_name(self):
        return f"{self.summary_id.code} - {self.barcode}"

    @api.depends('tax_ids', 'price_unit_incl', 'price_unit')
    def _compute_amount(self):
        for r in self:
            tax_results = r.tax_ids.compute_all(r.price_unit_incl, quantity=r.quantity)
            r.price_subtotal = tax_results["total_excluded"]
            r.amount_total = tax_results["total_included"]
            r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"]


class SummaryAccountMovePosLineDiscount(models.Model):
    _name = 'summary.account.move.pos.line.discount'

    line_pk = fields.Char('Line primary key')
    summary_line_id = fields.Many2one('summary.account.move.pos.line')
    summary_id = fields.Many2one('summary.account.move.pos', related="summary_line_id.summary_id")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    promotion_type = fields.Selection(
        selection=[
            ('point', 'Point'),
            ('card', 'Card'),
        ],
        string='Promotion Type', index=True, readonly=True
    )
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')


    summary_ids = fields.Many2many('summary.account.move.pos', string='Hóa đơn bán', relation='summary_account_move_pos_card_point_line_discount_rel')
    store_id = fields.Many2one('store')

    @api.depends('tax_ids', 'price_unit_incl')
    def _compute_amount(self):
        for r in self:
            if r.tax_ids:
                tax_results = r.tax_ids.compute_all(r.price_unit_incl)
                r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"] 
            else:
                r.tax_amount = 0

