# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from .utils import collect_pos_to_bkav_end_day, genarate_code, genarate_pos_code

class SummaryAccountMovePosReturn(models.Model):
    _name = 'summary.account.move.pos.return'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    store_id = fields.Many2one('store')
    partner_id = fields.Many2one('res.partner')
    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã phát hành')], string="State", default='draft')

    line_ids = fields.One2many('summary.account.move.pos.return.line', 'return_id')
    company_id = fields.Many2one('res.company')
    number_bill = fields.Char('Số hóa đơn')
    einvoice_status = fields.Selection([('draft', 'Draft')], string=' Trạng thái HDDT')
    einvoice_date = fields.Date(string="Ngày phát hành")


    def get_move_line(self, line):
        item = {
            "product_id": line.product_id.id,
            "quantity": line.qty,
            "price_unit": line.price_unit_excl,
            "price_unit_origin": line.refunded_orderline_id.price_unit_excl,
            "x_free_good": line.is_reward_line,
            "invoice_ids": [line.order_id.id],
            "tax_ids": line.tax_ids_after_fiscal_position.ids,
        }
        return item


    def include_line_by_product_and_price_bkav(self, lines):
        items = {}
        for line in lines:
            pk = f"{line.product_id.barcode}_{float(line.price_unit_excl)}"
            item = self.get_move_line(line)
            if items.get(pk):
                row = items[pk]
                row["quantity"] += item["quantity"]
                row["invoice_ids"].extend(item["invoice_ids"])
                row["invoice_ids"] = list(set(row["invoice_ids"]))
                # row["tax_ids"].extend(item["tax_ids"])
                # row["tax_ids"] = list(set(row["tax_ids"]))
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
        model_code = genarate_pos_code(typ='T', store_id=store, index=page)
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
        model = self.env['summary.account.move.pos.return']
        model_line = self.env['summary.account.move.pos.return.line']
        pos_code = None

        last_day = date.today()
        domain = [
            ('invoice_exists_bkav', '=', False),
            ('invoice_date', '<', last_day),
            ('is_post_bkav_store', '=', True),
            ('is_invoiced', '=', True),
            ('is_synthetic', '=', False),
        ]

        if kwargs.get("domain"):
            domain = kwargs["domain"]

        pos_order = self.env['pos.order'].search(domain)

        lines = self.env['pos.order.line'].search([
            ('order_id', 'in', pos_order.ids),
            ('refunded_orderline_id', '!=', False),
            ('qty', '<', 0),
            ('is_promotion', '=', False)
        ])
        data = {}
        items = {}
        pos_order_synthetic = None
        res_pos = None

        if lines:
            print('----------- INTO -------------------')
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

        return data, res_pos, pos_order_synthetic



    def collect_return_invoice_to_bkav_end_day(self, lines):
        model = self.env['summary.account.move.pos.return']
        model_line = self.env['summary.account.move.pos.return.line']
        return collect_pos_to_bkav_end_day(self, lines, model, model_line)



class SummaryAccountMovePosReturnLine(models.Model):
    _name = 'summary.account.move.pos.return.line'

    return_id = fields.Many2one('summary.account.move.pos.return')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    price_unit_origin = fields.Float('Đơn giá gốc')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="compute_price_subtotal")
    amount_total = fields.Monetary('Thành tiền', compute="compute_amount_total")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')

    def __str__(self):
        return f"{self.summary_id.code} - {self.barcode}"

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
                r.tax_amount = sum(r.tax_ids.mapped('amount')) * r.price_subtotal
            else:
                r.tax_amount = 0