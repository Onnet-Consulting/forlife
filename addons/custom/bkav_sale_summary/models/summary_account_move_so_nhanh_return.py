# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SummaryAccountMoveSoNhanhReturn(models.Model):
    _name = 'summary.account.move.so.nhanh.return'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    partner_id = fields.Many2one('res.partner')
    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã phát hành')], string="State", default='draft')
    line_ids = fields.One2many('summary.account.move.so.nhanh.return.line', 'summary_id')
    company_id = fields.Many2one('res.company')
    number_bill = fields.Char('Số hóa đơn')
    einvoice_status = fields.Selection([('draft', 'Draft')], string=' Trạng thái HDDT')
    einvoice_date = fields.Date(string="Ngày phát hành")

    line_discount_ids = fields.One2many('summary.so.nhanh.return.line.discount', compute="_compute_line_discount")

    def _compute_line_discount(self):
        for r in self:
            r.line_discount_ids = self.env["summary.so.nhanh.return.line.discount"].search([
                ('summary_id', '=', r.id)
            ])


class SummaryAccountMoveSoNhanhReturnLine(models.Model):
    _name = 'summary.account.move.so.nhanh.return.line'

    line_pk = fields.Char('Line primary key')
    summary_id = fields.Many2one('summary.account.move.so.nhanh.return')
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
    invoice_ids = fields.Many2many('account.move', string='Hóa đơn')

    line_ids = fields.One2many('summary.so.nhanh.return.line.discount', 'summary_line_id')

    @api.depends('tax_ids', 'price_unit_incl', 'price_unit')
    def _compute_amount(self):
        for r in self:
            tax_results = r.tax_ids.compute_all(r.price_unit_incl, quantity=r.quantity)
            r.price_subtotal = tax_results["total_excluded"]
            r.amount_total = tax_results["total_included"]
            r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"]




class SummaryAccountMoveSoNhanhReturnLineDiscount(models.Model):
    _name = 'summary.so.nhanh.return.line.discount'

    line_pk = fields.Char('Line primary key')
    summary_line_id = fields.Many2one('summary.account.move.so.nhanh.return.line')
    summary_id = fields.Many2one('summary.account.move.so.nhanh.return', related="summary_line_id.summary_id")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    promotion_type = fields.Selection(
        selection=[
            ('vip_amount', 'Vip'),
        ],
        string='Promotion Type', index=True, readonly=True
    )

    @api.depends('tax_ids', 'price_unit_incl', 'price_unit')
    def _compute_amount(self):
        for r in self:
            if r.tax_ids:
                tax_results = r.tax_ids.compute_all(r.price_unit_incl)
                r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"]

            else:
                r.tax_amount = 0

