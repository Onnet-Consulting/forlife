# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from ...bkav_connector.models import bkav_action


class SummaryAdjustedInvoiceSoNhanh(models.Model):
    _name = 'summary.adjusted.invoice.so.nhanh'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    partner_id = fields.Many2one('res.partner')
    source_invoice = fields.Many2one('synthetic.account.move.so.nhanh',
                                     string='Hóa đơn gốc')
    source_einvoice = fields.Char(string='Hóa đơn điện tử gốc')

    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã vào sổ')], string="State", default='draft')
    line_ids = fields.One2many('summary.adjusted.invoice.so.nhanh.line', 'adjusted_invoice_id')
    company_id = fields.Many2one('res.company')

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    invoice_guid = fields.Char('GUID HDDT')
    invoice_no = fields.Char('Số hóa đơn')
    invoice_form = fields.Char('Mẫu số HDDT')
    invoice_serial = fields.Char('Mẫu số - Ký hiệu hóa đơn')
    invoice_e_date = fields.Date(string="Ngày phát hành")
    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=True,
                                  copy=False)
    data_compare_status = fields.Selection([('1', 'Mới tạo'),
                                            ('2', 'Đã phát hành'),
                                            ('3', 'Đã hủy'),
                                            ('4', 'Đã xóa'),
                                            ('5', 'Chờ thay thế'),
                                            ('6', 'Thay thế'),
                                            ('7', 'Chờ điều chỉnh'),
                                            ('8', 'Điều chỉnh'),
                                            ('9', 'Bị thay thế'),
                                            ('10', 'Bị điều chỉnh'),
                                            ('11', 'Trống (Đã cấp số, Chờ ký)'),
                                            ('12', 'Không sử dụng'),
                                            ('13', 'Chờ huỷ'),
                                            ('14', 'Chờ điều chỉnh chiết khấu'),
                                            ('15', 'Điều chỉnh chiết khấu')], copy=False)
    partner_invoice_id = fields.Integer(string='Số hóa đơn')
    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)

    line_discount_ids = fields.One2many('adjusted.so.nhanh.line.discount', compute="_compute_line_discount")

    def _compute_line_discount(self):
        for r in self:
            r.line_discount_ids = self.env["adjusted.so.nhanh.line.discount"].search([
                ('adjusted_invoice_id', '=', r.id)
            ])
    
    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def action_download_view_e_invoice(self):
        return bkav_action.download_invoice_bkav(self)

    def get_invoice_bkav(self):
        bkav_action.get_invoice_bkav(self)

    def get_vat(self, line):
        vat = 0
        if line.tax_ids:
            vat = line.tax_ids[0].amount

        if vat == 0:
            tax_rate_id = 1
        elif vat == 5:
            tax_rate_id = 2
        elif vat == 8:
            tax_rate_id = 9
        elif vat == 10:
            tax_rate_id = 3
        else:
            tax_rate_id = 4
        return vat, tax_rate_id

    def get_item_type_bkav(self, line):
        item_type = 0
        if line.x_free_good:
            item_type = 15
        return item_type

    def get_bkav_data_pos(self):
        bkav_invoices = []
        for ln in self:
            invoice_date = fields.Datetime.context_timestamp(ln, datetime.combine(datetime.now(), datetime.now().time()))
            ln_invoice = {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": 'Khách lẻ',
                    "BuyerTaxCode": '',
                    "BuyerUnitName": 'Khách hàng không lấy hoá đơn',
                    "BuyerAddress":  '',
                    "BuyerBankAccount": "",
                    "PayMethodID": 3,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": str(ln.company_id.email).strip() if ln.company_id.email else '', 
                    "ReceiverMobile": str(ln.company_id.mobile).strip() if ln.company_id.mobile else '', 
                    "ReceiverAddress": str(ln.company_id.street).strip() if ln.company_id.street else '', 
                    "ReceiverName": str(ln.company_id.name).strip() if ln.company_id.name else '', 
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": str(ln.company_id.currency_id.name).strip() if ln.company_id.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    "OriginalInvoiceIdentify": ln.source_invoice.get_invoice_identify(),
                },
                "ListInvoiceDetailsWS": [],
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": ln.code,
            }
            for line in ln.line_ids:
                if line.product_id.voucher or line.product_id.is_voucher_auto:
                    continue
                    
                line_invoice = {
                    "ItemName": line.product_id.name if line.product_id.name else '',
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": line.price_unit,
                    "Amount": line.price_subtotal,
                    "TaxAmount": (line.tax_amount or 0.0),
                    "DiscountRate": 0.0,
                    "DiscountAmount":0.0,
                    "IsDiscount": 0,
                    "ItemTypeID": self.get_item_type_bkav(line),
                }
                vat, tax_rate_id = self.get_vat(line)
                line_invoice.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                ln_invoice["ListInvoiceDetailsWS"].append(line_invoice)

            bkav_invoices.append(ln_invoice)
        return bkav_invoices

    def create_an_invoice(self):
        for line in self:
            try:
                bkav_invoice_data = line.get_bkav_data_pos()
                bkav_action.create_invoice_bkav(
                    line, 
                    bkav_invoice_data, 
                    is_publish=True,
                    origin_id=line.source_invoice,
                    issue_invoice_type='adjust'
                )
            except Exception as e:
                line.message_post(body=str(e))


class SummaryAdjustedInvoiceSoNhanhLine(models.Model):
    _name = 'summary.adjusted.invoice.so.nhanh.line'

    line_pk = fields.Char('Line primary key')
    adjusted_invoice_id = fields.Many2one('summary.adjusted.invoice.so.nhanh')
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
    invoice_ids = fields.Many2many('account.move', string='Hóa đơn')

    line_ids = fields.One2many('adjusted.so.nhanh.line.discount', 'adjusted_line_id')

    @api.depends('price_subtotal', 'tax_amount')
    def compute_amount_total(self):
        for r in self:
            r.amount_total = -(abs(r.price_unit_incl * r.quantity) - r.discount_amount)

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = -(abs(r.price_unit * r.quantity) - r.discount_amount)

    @api.depends('tax_ids', 'price_subtotal')
    def compute_tax_amount(self):
        for r in self:
            if r.tax_ids:
                r.tax_amount = sum(r.tax_ids.mapped('amount')) * r.price_subtotal/100
            else:
                r.tax_amount = 0


class SummaryAdjustedInvoiceSoNhanhLineDiscount(models.Model):
    _name = 'adjusted.so.nhanh.line.discount'

    line_pk = fields.Char('Line primary key')
    adjusted_line_id = fields.Many2one('summary.adjusted.invoice.so.nhanh.line')
    adjusted_invoice_id = fields.Many2one('summary.adjusted.invoice.so.nhanh', related="adjusted_line_id.adjusted_invoice_id")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    amount_total = fields.Monetary('Thành tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    promotion_type = fields.Selection(
        selection=[
            ('vip_amount', 'Vip'),
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