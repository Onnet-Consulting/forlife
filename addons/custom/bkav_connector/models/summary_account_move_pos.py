# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class SummaryAccountMovePos(models.Model):
    _name = 'summary.account.move.pos'
    _rec_name = 'code'

    code = fields.Char('Code')
    partner_id = fields.Many2one('res.partner')
    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('posted', 'Posted')], string="State")
    line_ids = fields.One2many('summary.account.move.pos.line', 'summary_id')
    company_id = fields.Many2one('res.company')
    number_bill = fields.Char('Số hóa đơn')
    einvoice_status = fields.Selection([('draft', 'Draft')], string=' Trạng thái HDDT')
    einvoice_date = fields.Date(string="Ngày phát hành")

    def collect_bills_the_end_day(self):
        self.collect_invoice_sale_end_day()

    def collect_invoice_sale_end_day(self):
        moves = self.env['account.move']
        today = date.today()
        invoices = moves.search([('move_type', '=', 'out_invoice'),
                                 ('is_post_bkav', '=', False),
                                 ('pos_order_id', '!=', False),
                                 ('invoice_date', '<=', today)])
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
                            and line_id.product_id.standard_price == line2_id.product_id.standard_price and line_id.id != line2_id.id:
                        qty += line2_id.qty
                        invoice_ids.append(line2_id.order_id.id)
                        move_line.remove(line2)
                move_line_vals.append((0, 0, {
                    'product_id': line_id.product_id.id,
                    'quantity': qty,
                    'price_unit': line_id.product_id.standard_price,
                    'product_uom_id': line_id.product_id.standard_price,
                    'invoice_ids': [(6, 0, invoice_ids)]
                }))
            self.env['summary.account.move.pos'].create({
                'partner_id': store.contact_id.id,
                'invoice_date': date.today(),
                'line_ids': move_line_vals
            })


class SummaryAccountMovePosLine(models.Model):
    _name = 'summary.account.move.pos.line'

    summary_id = fields.Many2one('summary.account.move.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('% chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế', related="product_id.taxes_id")
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="compute_price_subtotal")
    amount_total = fields.Monetary('Thành tiền', compute="compute_amount_total")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.One2many('pos.order', 'move_pos_line_id', string='Hóa đơn')

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
