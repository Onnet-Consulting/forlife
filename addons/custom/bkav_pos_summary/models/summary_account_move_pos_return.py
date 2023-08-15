# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date
from .utils import genarate_pos_code

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

    line_discount_ids = fields.One2many('summary.account.move.pos.return.line.discount', compute="_compute_line_discount")

    def _compute_line_discount(self):
        for r in self:
            r.line_discount_ids = self.env["summary.account.move.pos.return.line.discount"].search([
                ('return_id', '=', r.id)
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

    def get_line_discount(self, line):
        line_discount_details = line.order_id.lines.filtered(
            lambda r: r.is_promotion == True and r.promotion_type in ['card','point'] and r.product_src_id.id == line.id
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
            "price_unit_origin": line.refunded_orderline_id.price_unit_excl,
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
        limit=1000,
        company_id=None
    ):
        model_code = genarate_pos_code(typ='T', store_id=store, index=page)
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
        model = self.env['summary.account.move.pos.return']
        model_line = self.env['summary.account.move.pos.return.line']
        pos_code = None

        last_day = date.today()
        domain = [
            ('is_general', '=', False),
            ('is_post_bkav_store', '=', True),
            ('exists_bkav', '=', False),
            ('pos_order_id', '!=', False),
            ('move_type', '=', 'out_refund'),
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
            ('refunded_orderline_id', '!=', False),
            ('qty', '<', 0),
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
                    limit=limit,
                    company_id=res[0].company_id
                )
                data[store.id] = line_items


            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res_pos = model.create(vals_list)

        return data, res_pos, move_ids



class SummaryAccountMovePosReturnLine(models.Model):
    _name = 'summary.account.move.pos.return.line'

    line_pk = fields.Char('Line primary key')
    return_id = fields.Many2one('summary.account.move.pos.return')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    price_unit_origin = fields.Float('Đơn giá gốc')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền', compute="_compute_amount")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')
    line_ids = fields.One2many('summary.account.move.pos.return.line.discount', 'summary_line_id')


    def __str__(self):
        return f"{self.summary_id.code} - {self.barcode}"

    @api.depends('tax_ids', 'price_unit_incl', 'price_unit')
    def _compute_amount(self):
        for r in self:
            tax_results = r.tax_ids.compute_all(r.price_unit_incl, quantity=r.quantity)
            r.price_subtotal = tax_results["total_excluded"]
            r.amount_total = tax_results["total_included"]
            r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"]


class SummaryAccountMovePosReturnLineDiscount(models.Model):
    _name = 'summary.account.move.pos.return.line.discount'

    line_pk = fields.Char('Line primary key')
    summary_line_id = fields.Many2one('summary.account.move.pos.return.line')
    return_id = fields.Many2one('summary.account.move.pos.return', related="summary_line_id.return_id")
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


    @api.depends('tax_ids', 'price_unit_incl')
    def _compute_amount(self):
        for r in self:
            if r.tax_ids:
                tax_results = r.tax_ids.compute_all(r.price_unit_incl)
                r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"] 
            else:
                r.tax_amount = 0

